"""Patrimony Client model."""

from datetime import datetime
from typing import Optional, TYPE_CHECKING
from uuid import uuid4

from sqlalchemy import String, Text, ForeignKey, Index, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from starke.infrastructure.database.base import Base

if TYPE_CHECKING:
    from starke.infrastructure.database.models import User
    from starke.infrastructure.database.patrimony.account import PatAccount
    from starke.infrastructure.database.patrimony.asset import PatAsset
    from starke.infrastructure.database.patrimony.liability import PatLiability
    from starke.infrastructure.database.patrimony.document import PatDocument


class PatClient(Base):
    """Patrimony client (PF, PJ, Family, Company).

    Represents a client whose patrimony is being managed.
    Can be linked to a User for self-service access.

    Fields:
    - user_id: Optional link to User for client login (self-service)
    - rm_user_id: Relationship Manager responsible for this client
    - cpf_cnpj_encrypted: Encrypted CPF/CNPJ (LGPD compliance)
    - cpf_cnpj_hash: Hash for searching without decryption
    """

    __tablename__ = "pat_clients"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        primary_key=True,
        default=lambda: str(uuid4()),
    )

    # Link to User for client login (optional - client may not have login)
    user_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        unique=True,  # One client per user
        index=True,
    )

    # Relationship Manager responsible for this client
    rm_user_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # Client info
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    client_type: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # pf, pj, family, company

    # CPF/CNPJ - encrypted for LGPD compliance
    cpf_cnpj_encrypted: Mapped[str] = mapped_column(
        String(500), nullable=False
    )  # Fernet encrypted
    cpf_cnpj_hash: Mapped[str] = mapped_column(
        String(64), nullable=False, unique=True
    )  # SHA256 hash for search

    # Contact info
    email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    phone: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)

    # Status
    status: Mapped[str] = mapped_column(
        String(50), nullable=False, default="active"
    )  # active, inactive, pending

    # Settings
    base_currency: Mapped[str] = mapped_column(String(3), nullable=False, default="BRL")
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(nullable=False, default=datetime.utcnow)
    updated_at: Mapped[Optional[datetime]] = mapped_column(
        nullable=True, onupdate=datetime.utcnow
    )

    # Relationships
    user: Mapped[Optional["User"]] = relationship(
        "User",
        foreign_keys=[user_id],
        lazy="joined",
    )
    rm_user: Mapped[Optional["User"]] = relationship(
        "User",
        foreign_keys=[rm_user_id],
        lazy="joined",
    )
    accounts: Mapped[list["PatAccount"]] = relationship(
        "PatAccount",
        back_populates="client",
        cascade="all, delete-orphan",
        lazy="dynamic",
    )
    assets: Mapped[list["PatAsset"]] = relationship(
        "PatAsset",
        back_populates="client",
        cascade="all, delete-orphan",
        lazy="dynamic",
    )
    liabilities: Mapped[list["PatLiability"]] = relationship(
        "PatLiability",
        back_populates="client",
        cascade="all, delete-orphan",
        lazy="dynamic",
    )
    documents: Mapped[list["PatDocument"]] = relationship(
        "PatDocument",
        back_populates="client",
        cascade="all, delete-orphan",
        lazy="dynamic",
    )

    __table_args__ = (
        Index("idx_pat_clients_type", "client_type"),
        Index("idx_pat_clients_status", "status"),
        Index("idx_pat_clients_rm", "rm_user_id"),
        Index("idx_pat_clients_user", "user_id"),
        Index("idx_pat_clients_name", "name"),
    )

    def __repr__(self) -> str:
        return f"<PatClient(id={self.id}, name={self.name}, type={self.client_type})>"

    @property
    def has_login(self) -> bool:
        """Check if client has a login user."""
        return self.user_id is not None
