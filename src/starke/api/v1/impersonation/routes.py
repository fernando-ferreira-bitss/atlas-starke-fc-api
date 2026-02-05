"""Rotas de Impersonation.

Permite que usuários admin/rm visualizem o portal como um cliente específico.
"""

from datetime import datetime, timedelta, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from starke.api.dependencies.auth import get_current_active_user, require_role
from starke.api.dependencies.database import get_db
from starke.api.v1.impersonation.schemas import (
    ActorInfo,
    ImpersonationStartRequest,
    ImpersonationStartResponse,
    ImpersonationStatusResponse,
    ImpersonationStopResponse,
    TargetInfo,
)
from starke.domain.services.impersonation_service import (
    IMPERSONATION_TTL_HOURS,
    ImpersonationService,
)
from starke.infrastructure.database.models import User, UserRole
from starke.infrastructure.database.patrimony.client import PatClient

router = APIRouter()


@router.post("/start", response_model=ImpersonationStartResponse)
def start_impersonation(
    request_data: ImpersonationStartRequest,
    current_user: Annotated[User, Depends(require_role(UserRole.ADMIN, UserRole.RM))],
    db: Annotated[Session, Depends(get_db)],
):
    """Inicia uma sessão de impersonation.

    Permite que um admin ou RM visualize o portal como um cliente específico.
    O token retornado deve ser usado nas requisições subsequentes.

    - **Admin**: Pode impersonar qualquer cliente
    - **RM**: Só pode impersonar clientes atribuídos a ele
    """
    service = ImpersonationService(db)

    token, log, error = service.start_impersonation(
        actor=current_user,
        client_id=request_data.client_id,
    )

    if error:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=error,
        )

    # Buscar informações do cliente
    client, target_user = service.get_client_with_user(request_data.client_id)

    expires_at = datetime.now(timezone.utc) + timedelta(hours=IMPERSONATION_TTL_HOURS)

    return ImpersonationStartResponse(
        impersonation_token=token,
        actor=ActorInfo(
            id=current_user.id,
            email=current_user.email,
            role=current_user.role,
        ),
        target=TargetInfo(
            user_id=target_user.id,
            client_id=client.id,
            client_name=client.name,
            email=client.email,
        ),
        expires_at=expires_at,
        read_only=True,
    )


@router.post("/stop", response_model=ImpersonationStopResponse)
def stop_impersonation(
    request: Request,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[Session, Depends(get_db)],
):
    """Encerra a sessão de impersonation atual.

    O token de impersonation deve ser descartado pelo frontend após esta chamada.
    """
    # Verificar se está em modo impersonation
    if not hasattr(request.state, "impersonation_context"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Não há sessão de impersonation ativa",
        )

    ctx = request.state.impersonation_context
    service = ImpersonationService(db)

    success = service.stop_impersonation(ctx.impersonation_log_id)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Não foi possível encerrar a sessão de impersonation",
        )

    return ImpersonationStopResponse(
        message="Sessão de impersonation encerrada com sucesso",
        actor=ActorInfo(
            id=ctx.actor_user_id,
            email=ctx.actor_email,
            role=ctx.actor_role,
        ),
    )


@router.get("/status", response_model=ImpersonationStatusResponse)
def get_impersonation_status(
    request: Request,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[Session, Depends(get_db)],
):
    """Verifica o status da sessão de impersonation atual.

    Retorna informações sobre quem está impersonando e qual cliente está sendo visualizado.
    """
    # Verificar se está em modo impersonation
    if not hasattr(request.state, "impersonation_context"):
        return ImpersonationStatusResponse(is_impersonating=False)

    ctx = request.state.impersonation_context
    service = ImpersonationService(db)

    # Buscar informações do cliente
    client, target_user = service.get_client_with_user(ctx.target_client_id)

    # Calcular tempo de expiração (baseado no TTL padrão)
    expires_at = datetime.now(timezone.utc) + timedelta(hours=IMPERSONATION_TTL_HOURS)

    return ImpersonationStatusResponse(
        is_impersonating=True,
        actor=ActorInfo(
            id=ctx.actor_user_id,
            email=ctx.actor_email,
            role=ctx.actor_role,
        ),
        target=TargetInfo(
            user_id=ctx.target_user_id,
            client_id=ctx.target_client_id,
            client_name=client.name if client else "Unknown",
            email=client.email if client else None,
        ),
        started_at=None,  # Seria necessário buscar do log
        expires_at=expires_at,
        read_only=ctx.is_read_only,
    )
