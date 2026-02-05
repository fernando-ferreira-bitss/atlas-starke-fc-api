"""Serviço de Impersonation.

Permite que usuários admin/rm visualizem o portal como um cliente específico.
"""

from datetime import datetime, timedelta, timezone
from typing import Optional, Tuple

from jose import jwt
from sqlalchemy import select
from sqlalchemy.orm import Session

from starke.core.config import get_settings
from starke.infrastructure.database.models import (
    ImpersonationLog,
    User,
    UserRole,
)
from starke.infrastructure.database.patrimony.client import PatClient


# Tempo de expiração do token de impersonation (1 hora)
IMPERSONATION_TTL_HOURS = 1


class ImpersonationService:
    """Serviço para gerenciar sessões de impersonation."""

    def __init__(self, db: Session):
        self.db = db

    def can_impersonate(self, actor: User, client_id: str) -> Tuple[bool, str]:
        """Verifica se o usuário pode impersonar o cliente.

        Args:
            actor: Usuário que quer impersonar
            client_id: ID do PatClient a ser impersonado

        Returns:
            Tuple (pode_impersonar, motivo)
        """
        # Admin pode impersonar qualquer cliente
        if actor.is_admin:
            return True, "Admin tem acesso total"

        # RM só pode impersonar clientes atribuídos a ele via PatClient.rm_user_id
        if actor.role == UserRole.RM.value:
            client = self.db.execute(
                select(PatClient).where(PatClient.id == client_id)
            ).scalar_one_or_none()

            if not client:
                return False, "Cliente não encontrado"

            # Verificar se RM é responsável pelo cliente
            if client.rm_user_id == actor.id:
                return True, "RM é responsável pelo cliente"

            return False, "RM não tem acesso a este cliente"

        return False, "Role não tem permissão para impersonation"

    def get_client_with_user(self, client_id: str) -> Tuple[Optional[PatClient], Optional[User]]:
        """Busca o cliente e o usuário vinculado.

        Args:
            client_id: ID do PatClient

        Returns:
            Tuple (PatClient, User) ou (None, None) se não encontrado
        """
        client = self.db.execute(
            select(PatClient).where(PatClient.id == client_id)
        ).scalar_one_or_none()

        if not client:
            return None, None

        if not client.user_id:
            return client, None

        user = self.db.execute(
            select(User).where(User.id == client.user_id)
        ).scalar_one_or_none()

        return client, user

    def start_impersonation(
        self,
        actor: User,
        client_id: str,
    ) -> Tuple[Optional[str], Optional[ImpersonationLog], str]:
        """Inicia uma sessão de impersonation.

        Args:
            actor: Usuário que está impersonando
            client_id: ID do PatClient a ser impersonado

        Returns:
            Tuple (token, log, mensagem_erro)
        """
        # Verificar permissão
        can_impersonate, reason = self.can_impersonate(actor, client_id)
        if not can_impersonate:
            return None, None, reason

        # Buscar cliente e usuário vinculado
        client, target_user = self.get_client_with_user(client_id)

        if not client:
            return None, None, "Cliente não encontrado"

        if not target_user:
            return None, None, "Cliente não possui usuário vinculado para login"

        if not target_user.is_active:
            return None, None, "Usuário do cliente está inativo"

        # Criar registro de log
        log = ImpersonationLog(
            actor_user_id=actor.id,
            target_client_id=client_id,
            target_user_id=target_user.id,
            started_at=datetime.now(timezone.utc),
        )
        self.db.add(log)
        self.db.commit()
        self.db.refresh(log)

        # Gerar token de impersonation
        token = self.create_impersonation_token(
            actor_email=actor.email,
            actor_user_id=actor.id,
            target_user_id=target_user.id,
            target_client_id=client_id,
            impersonation_log_id=log.id,
        )

        return token, log, ""

    def stop_impersonation(self, log_id: int) -> bool:
        """Encerra uma sessão de impersonation.

        Args:
            log_id: ID do registro de impersonation

        Returns:
            True se encerrado com sucesso
        """
        log = self.db.execute(
            select(ImpersonationLog).where(ImpersonationLog.id == log_id)
        ).scalar_one_or_none()

        if not log:
            return False

        if log.ended_at:
            return False  # Já foi encerrado

        log.ended_at = datetime.now(timezone.utc)
        self.db.commit()
        return True

    def get_active_impersonation(self, actor_user_id: int) -> Optional[ImpersonationLog]:
        """Busca sessão de impersonation ativa para o usuário.

        Args:
            actor_user_id: ID do usuário que está impersonando

        Returns:
            ImpersonationLog ativo ou None
        """
        return self.db.execute(
            select(ImpersonationLog)
            .where(ImpersonationLog.actor_user_id == actor_user_id)
            .where(ImpersonationLog.ended_at.is_(None))
            .order_by(ImpersonationLog.started_at.desc())
        ).scalar_one_or_none()

    @staticmethod
    def create_impersonation_token(
        actor_email: str,
        actor_user_id: int,
        target_user_id: int,
        target_client_id: str,
        impersonation_log_id: int,
    ) -> str:
        """Cria um token JWT de impersonation.

        Args:
            actor_email: Email do usuário que está impersonando
            actor_user_id: ID do usuário que está impersonando
            target_user_id: ID do usuário sendo impersonado
            target_client_id: ID do PatClient sendo impersonado
            impersonation_log_id: ID do registro de log

        Returns:
            Token JWT de impersonation
        """
        settings = get_settings()

        expire = datetime.now(timezone.utc) + timedelta(hours=IMPERSONATION_TTL_HOURS)

        payload = {
            "sub": actor_email,
            "type": "impersonation",
            "actor_user_id": actor_user_id,
            "target_user_id": target_user_id,
            "target_client_id": target_client_id,
            "impersonation_log_id": impersonation_log_id,
            "read_only": True,
            "exp": expire,
        }

        return jwt.encode(
            payload,
            settings.jwt_secret_key,
            algorithm=settings.jwt_algorithm,
        )

    @staticmethod
    def decode_impersonation_token(token: str) -> Optional[dict]:
        """Decodifica um token de impersonation.

        Args:
            token: Token JWT

        Returns:
            Payload decodificado ou None se inválido
        """
        from jose import JWTError

        settings = get_settings()

        try:
            payload = jwt.decode(
                token,
                settings.jwt_secret_key,
                algorithms=[settings.jwt_algorithm],
            )

            # Verificar se é um token de impersonation
            if payload.get("type") != "impersonation":
                return None

            return payload
        except JWTError:
            return None
