"""Financial Institution model."""

from datetime import datetime
from typing import Optional
from uuid import uuid4

from sqlalchemy import String, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from starke.infrastructure.database.base import Base


class PatInstitution(Base):
    """Financial institutions (banks, brokers, insurance companies).

    Used to categorize accounts and liabilities by institution.
    """

    __tablename__ = "pat_institutions"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        primary_key=True,
        default=lambda: str(uuid4()),
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    code: Mapped[Optional[str]] = mapped_column(
        String(50), nullable=True
    )  # Bank code, CNPJ, etc.
    institution_type: Mapped[str] = mapped_column(
        String(50), nullable=False, default="bank"
    )  # bank, broker, insurance, other
    is_active: Mapped[bool] = mapped_column(nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(nullable=False, default=datetime.utcnow)
    updated_at: Mapped[Optional[datetime]] = mapped_column(
        nullable=True, onupdate=datetime.utcnow
    )

    __table_args__ = (
        Index("idx_pat_institutions_name", "name"),
        Index("idx_pat_institutions_type", "institution_type"),
        Index("idx_pat_institutions_active", "is_active"),
    )

    def __repr__(self) -> str:
        return f"<PatInstitution(id={self.id}, name={self.name}, type={self.institution_type})>"
