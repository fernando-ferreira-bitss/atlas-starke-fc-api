"""Patrimony Asset model."""

from datetime import date, datetime
from decimal import Decimal
from typing import Optional, TYPE_CHECKING
from uuid import uuid4

from sqlalchemy import String, Text, Numeric, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from starke.infrastructure.database.base import Base

if TYPE_CHECKING:
    from starke.infrastructure.database.patrimony.client import PatClient
    from starke.infrastructure.database.patrimony.account import PatAccount
    from starke.infrastructure.database.patrimony.monthly_position import PatMonthlyPosition
    from starke.infrastructure.database.patrimony.document import PatDocument


class PatAsset(Base):
    """Patrimony asset.

    Represents an asset owned by a client.

    Categories:
    - fixed_income: Renda Fixa (CDB, LCI, LCA, Tesouro, etc.)
    - variable_income: Renda Variável (Ações, FIIs, ETFs, etc.)
    - real_estate: Imóveis
    - participations: Participações societárias
    - alternatives: Alternativos (Criptomoedas, Commodities, etc.)
    - cash: Disponibilidades
    - other: Outros
    """

    __tablename__ = "pat_assets"

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
    account_id: Mapped[Optional[str]] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("pat_accounts.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # Asset info
    category: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # fixed_income, variable_income, real_estate, etc.
    subcategory: Mapped[Optional[str]] = mapped_column(
        String(50), nullable=True
    )  # More specific classification
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    ticker: Mapped[Optional[str]] = mapped_column(
        String(20), nullable=True
    )  # For stocks, funds, etc.

    # Values
    base_value: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(18, 2), nullable=True
    )  # Original/acquisition value
    current_value: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(18, 2), nullable=True
    )  # Current market value
    quantity: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(18, 6), nullable=True
    )  # For stocks, crypto, etc.

    # Dates
    base_date: Mapped[Optional[date]] = mapped_column(nullable=True)  # Acquisition date
    base_year: Mapped[Optional[int]] = mapped_column(nullable=True)
    maturity_date: Mapped[Optional[date]] = mapped_column(
        nullable=True
    )  # For fixed income

    # Settings
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="BRL")
    is_active: Mapped[bool] = mapped_column(nullable=False, default=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(nullable=False, default=datetime.utcnow)
    updated_at: Mapped[Optional[datetime]] = mapped_column(
        nullable=True, onupdate=datetime.utcnow
    )

    # Relationships
    client: Mapped["PatClient"] = relationship(
        "PatClient",
        back_populates="assets",
        lazy="joined",
    )
    account: Mapped[Optional["PatAccount"]] = relationship(
        "PatAccount",
        back_populates="assets",
        lazy="joined",
    )
    positions: Mapped[list["PatMonthlyPosition"]] = relationship(
        "PatMonthlyPosition",
        back_populates="asset",
        cascade="all, delete-orphan",
        lazy="dynamic",
    )
    documents: Mapped[list["PatDocument"]] = relationship(
        "PatDocument",
        back_populates="asset",
        lazy="dynamic",
    )

    __table_args__ = (
        Index("idx_pat_assets_client", "client_id"),
        Index("idx_pat_assets_account", "account_id"),
        Index("idx_pat_assets_category", "category"),
        Index("idx_pat_assets_active", "is_active"),
        Index("idx_pat_assets_ticker", "ticker"),
    )

    def __repr__(self) -> str:
        return f"<PatAsset(id={self.id}, name={self.name}, category={self.category})>"

    @property
    def variation(self) -> Optional[Decimal]:
        """Calculate variation between base and current value."""
        if self.base_value and self.current_value and self.base_value > 0:
            return ((self.current_value - self.base_value) / self.base_value) * 100
        return None
