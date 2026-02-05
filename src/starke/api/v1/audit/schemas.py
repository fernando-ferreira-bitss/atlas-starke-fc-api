"""Schemas for audit log endpoints."""

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field


class AuditLogResponse(BaseModel):
    """Response schema for audit log entry."""

    id: str
    user_id: Optional[int] = None
    user_email: Optional[str] = None  # Populated via join
    action: str
    entity_type: Optional[str] = None
    entity_id: Optional[str] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    details: Optional[dict[str, Any]] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class AuditLogListResponse(BaseModel):
    """Response schema for paginated audit logs."""

    items: list[AuditLogResponse]
    total: int
    page: int
    per_page: int
    pages: int


class AuditLogFilter(BaseModel):
    """Filter schema for querying audit logs."""

    user_id: Optional[int] = Field(None, description="Filter by user ID")
    action: Optional[str] = Field(
        None, description="Filter by action (create, read, update, delete, export, login, logout)"
    )
    entity_type: Optional[str] = Field(
        None, description="Filter by entity type (pat_clients, pat_assets, etc.)"
    )
    entity_id: Optional[str] = Field(None, description="Filter by entity ID")
    ip_address: Optional[str] = Field(None, description="Filter by IP address")
    start_date: Optional[datetime] = Field(None, description="Filter from date")
    end_date: Optional[datetime] = Field(None, description="Filter until date")


class AuditStatsResponse(BaseModel):
    """Response schema for audit statistics."""

    total_actions: int
    actions_by_type: dict[str, int]
    actions_by_entity: dict[str, int]
    top_users: list[dict[str, Any]]
    recent_logins: int
    recent_failures: int
