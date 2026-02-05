"""Patrimony Liability model."""

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
    from starke.infrastructure.database.patrimony.institution import PatInstitution
    from starke.infrastructure.database.patrimony.document import PatDocument


class PatLiability(Base):
    """Patrimony liability.

    Represents a debt or obligation of a client.

    Types:
    - mortgage: Financiamento imobiliário
    - vehicle_loan: Financiamento de veículo
    - personal_loan: Empréstimo pessoal
    - credit_card: Cartão de crédito
    - overdraft: Cheque especial
    - other: Outros
    """

    __tablename__ = "pat_liabilities"

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

    # Liability info
    liability_type: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # mortgage, personal_loan, credit_card, etc.
    description: Mapped[str] = mapped_column(String(255), nullable=False)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Values
    original_amount: Mapped[Decimal] = mapped_column(
        Numeric(18, 2), nullable=False
    )  # Original debt value
    current_balance: Mapped[Decimal] = mapped_column(
        Numeric(18, 2), nullable=False
    )  # Current outstanding balance
    monthly_payment: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(18, 2), nullable=True
    )  # Monthly installment
    interest_rate: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(8, 4), nullable=True
    )  # Annual interest rate (%)

    # Dates
    start_date: Mapped[Optional[date]] = mapped_column(nullable=True)  # Contract start
    end_date: Mapped[Optional[date]] = mapped_column(nullable=True)  # Expected payoff date
    last_payment_date: Mapped[Optional[date]] = mapped_column(nullable=True)

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
        back_populates="liabilities",
        lazy="joined",
    )
    institution: Mapped[Optional["PatInstitution"]] = relationship(
        "PatInstitution",
        lazy="joined",
    )
    documents: Mapped[list["PatDocument"]] = relationship(
        "PatDocument",
        back_populates="liability",
        lazy="dynamic",
    )

    __table_args__ = (
        Index("idx_pat_liabilities_client", "client_id"),
        Index("idx_pat_liabilities_institution", "institution_id"),
        Index("idx_pat_liabilities_type", "liability_type"),
        Index("idx_pat_liabilities_active", "is_active"),
    )

    def __repr__(self) -> str:
        return f"<PatLiability(id={self.id}, type={self.liability_type}, balance={self.current_balance})>"

    @property
    def is_paid_off(self) -> bool:
        """Check if liability is fully paid."""
        return self.current_balance <= 0
