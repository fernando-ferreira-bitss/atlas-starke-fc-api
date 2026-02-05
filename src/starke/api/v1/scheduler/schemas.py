"""Schemas for Scheduler API."""

from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class SyncOrigin(str, Enum):
    """Sync origin options."""
    MEGA = "mega"
    UAU = "uau"
    BOTH = "both"


class SyncRequest(BaseModel):
    """Request body for sync trigger."""

    origem: SyncOrigin = Field(
        default=SyncOrigin.MEGA,
        description="Origem dos dados: mega, uau ou both"
    )
    start_date: Optional[str] = Field(
        None,
        description="Data inicial (YYYY-MM-DD). Default: 12 meses atrás"
    )
    end_date: Optional[str] = Field(
        None,
        description="Data final (YYYY-MM-DD). Default: hoje"
    )
    empresa_ids: Optional[List[int]] = Field(
        None,
        description="IDs de empresas/empreendimentos específicos"
    )


class SyncResponse(BaseModel):
    """Sync trigger response with details."""

    status: str
    message: str
    origem: str
    stats: Optional[Dict[str, Any]] = None


class SchedulerStatus(BaseModel):
    """Scheduler status response."""

    running: bool
    next_run: Optional[str] = None
    schedule: str
    timezone: str


class RunResponse(BaseModel):
    """Run details response."""

    id: int
    exec_date: str
    status: str
    started_at: str
    finished_at: Optional[str] = None
    duration_seconds: Optional[float] = None
    error: Optional[str] = None
    metrics: Optional[Dict[str, Any]] = None
    triggered_by_user_id: Optional[int] = None  # NULL = scheduler, ID = manual trigger


class RunListResponse(BaseModel):
    """Paginated list of runs."""

    items: List[RunResponse]
    total: int
    page: int
    per_page: int
    pages: int


class TriggerResponse(BaseModel):
    """Manual trigger response."""

    status: str
    message: str
