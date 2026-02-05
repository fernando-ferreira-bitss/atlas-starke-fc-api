"""Monthly Position model."""

from datetime import date, datetime
from decimal import Decimal
from typing import Optional, TYPE_CHECKING
from uuid import uuid4

from sqlalchemy import String, Numeric, ForeignKey, Index, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from starke.infrastructure.database.base import Base

if TYPE_CHECKING:
    from starke.infrastructure.database.patrimony.client import PatClient
    from starke.infrastructure.database.patrimony.asset import PatAsset


class PatMonthlyPosition(Base):
    """Monthly position of an asset.

    Tracks the value of an asset at a specific point in time.
    Used for building historical evolution charts.
    """

    __tablename__ = "pat_monthly_positions"

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
    asset_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("pat_assets.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Position info
    reference_date: Mapped[date] = mapped_column(nullable=False, index=True)
    value: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    quantity: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(18, 6), nullable=True
    )  # For assets with quantity
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="BRL")

    # Source tracking
    source: Mapped[str] = mapped_column(
        String(50), nullable=False, default="manual"
    )  # manual, spreadsheet, api
    import_batch_id: Mapped[Optional[str]] = mapped_column(
        UUID(as_uuid=False), nullable=True
    )  # Link to import log

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(nullable=False, default=datetime.utcnow)

    # Relationships
    client: Mapped["PatClient"] = relationship("PatClient", lazy="joined")
    asset: Mapped["PatAsset"] = relationship(
        "PatAsset",
        back_populates="positions",
        lazy="joined",
    )

    __table_args__ = (
        UniqueConstraint("asset_id", "reference_date", name="uq_pat_position_asset_date"),
        Index("idx_pat_positions_client", "client_id"),
        Index("idx_pat_positions_asset", "asset_id"),
        Index("idx_pat_positions_date", "reference_date"),
        Index("idx_pat_positions_source", "source"),
    )

    def __repr__(self) -> str:
        return f"<PatMonthlyPosition(asset={self.asset_id}, date={self.reference_date}, value={self.value})>"
