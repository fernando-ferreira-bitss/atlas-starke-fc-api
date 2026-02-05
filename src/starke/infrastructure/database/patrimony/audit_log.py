"""Audit Log model for LGPD compliance."""

from datetime import datetime
from typing import Any, Optional
from uuid import uuid4

from sqlalchemy import JSON, String, Text, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from starke.infrastructure.database.base import Base


class PatAuditLog(Base):
    """Audit log for LGPD compliance.

    Records all sensitive data access and modifications.

    Actions:
    - create: Record created
    - read: Record accessed
    - update: Record modified
    - delete: Record deleted
    - export: Data exported
    - login: User logged in
    - logout: User logged out
    """

    __tablename__ = "pat_audit_logs"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        primary_key=True,
        default=lambda: str(uuid4()),
    )

    # Who performed the action
    user_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # What was done
    action: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # create, read, update, delete, export, login, logout

    # What was affected
    entity_type: Mapped[Optional[str]] = mapped_column(
        String(100), nullable=True
    )  # pat_clients, pat_assets, etc.
    entity_id: Mapped[Optional[str]] = mapped_column(
        UUID(as_uuid=False), nullable=True
    )

    # Request context
    ip_address: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    user_agent: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Additional details (JSON)
    details: Mapped[Optional[dict[str, Any]]] = mapped_column(JSON, nullable=True)
    # Details can include:
    # - old_values: Previous values before update
    # - new_values: New values after update
    # - fields_accessed: List of fields read
    # - export_format: Format of exported data
    # - reason: Reason for action

    # Timestamp (not updatable - audit logs are immutable)
    created_at: Mapped[datetime] = mapped_column(nullable=False, default=datetime.utcnow)

    __table_args__ = (
        Index("idx_pat_audit_user", "user_id"),
        Index("idx_pat_audit_action", "action"),
        Index("idx_pat_audit_entity_type", "entity_type"),
        Index("idx_pat_audit_entity_id", "entity_id"),
        Index("idx_pat_audit_created_at", "created_at"),
        Index("idx_pat_audit_ip", "ip_address"),
    )

    def __repr__(self) -> str:
        return f"<PatAuditLog(id={self.id}, action={self.action}, entity={self.entity_type})>"
