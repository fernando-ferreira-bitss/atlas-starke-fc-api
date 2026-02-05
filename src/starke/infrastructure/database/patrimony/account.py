"""Patrimony Account model."""

from datetime import date, datetime
from typing import Optional, TYPE_CHECKING
from uuid import uuid4

from sqlalchemy import String, Text, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from starke.infrastructure.database.base import Base

if TYPE_CHECKING:
    from starke.infrastructure.database.patrimony.client import PatClient
    from starke.infrastructure.database.patrimony.institution import PatInstitution
    from starke.infrastructure.database.patrimony.asset import PatAsset


class PatAccount(Base):
    """Bank or brokerage account.

    Represents a financial account that can hold multiple assets.
    """

    __tablename__ = "pat_accounts"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        primary_key=True,
        default=lambda: str(uuid4()),
    )

    # Foreign keys
    client_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("pat_clients.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    institution_id: Mapped[Optional[str]] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("pat_institutions.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # Account info
    account_type: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # checking, savings, investment, brokerage
    account_number: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    agency: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="BRL")
    base_date: Mapped[Optional[date]] = mapped_column(nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Status
    is_active: Mapped[bool] = mapped_column(nullable=False, default=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(nullable=False, default=datetime.utcnow)
    updated_at: Mapped[Optional[datetime]] = mapped_column(
        nullable=True, onupdate=datetime.utcnow
    )

    # Relationships
    client: Mapped["PatClient"] = relationship(
        "PatClient",
        back_populates="accounts",
        lazy="joined",
    )
    institution: Mapped[Optional["PatInstitution"]] = relationship(
        "PatInstitution",
        lazy="joined",
    )
    assets: Mapped[list["PatAsset"]] = relationship(
        "PatAsset",
        back_populates="account",
        lazy="dynamic",
    )

    __table_args__ = (
        Index("idx_pat_accounts_client", "client_id"),
        Index("idx_pat_accounts_institution", "institution_id"),
        Index("idx_pat_accounts_type", "account_type"),
        Index("idx_pat_accounts_active", "is_active"),
    )

    def __repr__(self) -> str:
        return f"<PatAccount(id={self.id}, type={self.account_type}, client={self.client_id})>"
