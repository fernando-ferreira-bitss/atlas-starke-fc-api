"""Import History model."""

from datetime import datetime
from typing import Optional
from uuid import uuid4

from sqlalchemy import String, Text, Integer
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from starke.infrastructure.database.base import Base


class PatImportHistory(Base):
    """Import history for position uploads.

    Tracks all spreadsheet imports with metadata and status.
    """

    __tablename__ = "pat_import_history"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        primary_key=True,
        default=lambda: str(uuid4()),
    )

    # File info
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    file_path: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    file_size: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Import details
    reference_date: Mapped[str] = mapped_column(
        String(10), nullable=False
    )  # YYYY-MM-DD format
    imported_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    error_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # Status
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="pending"
    )  # pending, processing, success, error

    # Error details (JSON stored as text)
    errors: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # User tracking
    uploaded_by: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    uploaded_by_id: Mapped[Optional[str]] = mapped_column(
        UUID(as_uuid=False), nullable=True
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(nullable=False, default=datetime.utcnow)
    completed_at: Mapped[Optional[datetime]] = mapped_column(nullable=True)

    def __repr__(self) -> str:
        return f"<PatImportHistory(id={self.id}, file={self.file_name}, status={self.status})>"
