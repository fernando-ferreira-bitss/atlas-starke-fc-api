"""Schemas para Impersonation."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class ActorInfo(BaseModel):
    """Informações do usuário que está impersonando."""

    id: int
    email: str
    role: str


class TargetInfo(BaseModel):
    """Informações do cliente sendo impersonado."""

    user_id: int
    client_id: str
    client_name: str
    email: Optional[str] = None


class ImpersonationStartRequest(BaseModel):
    """Request para iniciar impersonation."""

    client_id: str


class ImpersonationStartResponse(BaseModel):
    """Response ao iniciar impersonation."""

    impersonation_token: str
    actor: ActorInfo
    target: TargetInfo
    expires_at: datetime
    read_only: bool = True


class ImpersonationStatusResponse(BaseModel):
    """Status da sessão de impersonation."""

    is_impersonating: bool
    actor: Optional[ActorInfo] = None
    target: Optional[TargetInfo] = None
    started_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    read_only: bool = True


class ImpersonationStopResponse(BaseModel):
    """Response ao encerrar impersonation."""

    message: str
    actor: ActorInfo
