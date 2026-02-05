"""Document model for S3 storage."""

from datetime import datetime
from typing import Optional, TYPE_CHECKING
from uuid import uuid4

from sqlalchemy import String, Text, Integer, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from starke.infrastructure.database.base import Base

if TYPE_CHECKING:
    from starke.infrastructure.database.models import User
    from starke.infrastructure.database.patrimony.client import PatClient
    from starke.infrastructure.database.patrimony.account import PatAccount
    from starke.infrastructure.database.patrimony.asset import PatAsset
    from starke.infrastructure.database.patrimony.liability import PatLiability


class PatDocument(Base):
    """Document stored in S3.

    Documents can be associated with clients, accounts, or assets.

    Types:
    - contract: Contratos
    - report: Relatórios
    - statement: Extratos
    - certificate: Certificados
    - proof: Comprovantes
    - other: Outros
    """

    __tablename__ = "pat_documents"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        primary_key=True,
        default=lambda: str(uuid4()),
    )

    # Associations (at least client_id is required)
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
    asset_id: Mapped[Optional[str]] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("pat_assets.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    liability_id: Mapped[Optional[str]] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("pat_liabilities.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # Document info
    document_type: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # contract, report, statement, etc.
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # File info
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    s3_key: Mapped[str] = mapped_column(
        String(500), nullable=False
    )  # Full S3 path: documents/{client_id}/{type}/{filename}
    file_size: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)  # Size in bytes
    mime_type: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    # Metadata
    reference_date: Mapped[Optional[datetime]] = mapped_column(
        nullable=True
    )  # Document reference date
    uploaded_by: Mapped[Optional[int]] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Validation status
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="pending"
    )  # pending, validated, rejected
    validated_by: Mapped[Optional[int]] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    validated_at: Mapped[Optional[datetime]] = mapped_column(nullable=True)
    validation_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(nullable=False, default=datetime.utcnow)
    updated_at: Mapped[Optional[datetime]] = mapped_column(
        nullable=True, onupdate=datetime.utcnow
    )

    # Relationships
    client: Mapped["PatClient"] = relationship(
        "PatClient",
        back_populates="documents",
        lazy="joined",
    )
    account: Mapped[Optional["PatAccount"]] = relationship("PatAccount", lazy="joined")
    asset: Mapped[Optional["PatAsset"]] = relationship(
        "PatAsset",
        back_populates="documents",
        lazy="joined",
    )
    liability: Mapped[Optional["PatLiability"]] = relationship(
        "PatLiability",
        back_populates="documents",
        lazy="joined",
    )
    uploader: Mapped[Optional["User"]] = relationship(
        "User",
        foreign_keys=[uploaded_by],
        lazy="joined",
    )
    validator: Mapped[Optional["User"]] = relationship(
        "User",
        foreign_keys=[validated_by],
        lazy="joined",
    )

    __table_args__ = (
        Index("idx_pat_documents_client", "client_id"),
        Index("idx_pat_documents_account", "account_id"),
        Index("idx_pat_documents_asset", "asset_id"),
        Index("idx_pat_documents_liability", "liability_id"),
        Index("idx_pat_documents_type", "document_type"),
        Index("idx_pat_documents_uploaded_by", "uploaded_by"),
        Index("idx_pat_documents_status", "status"),
    )

    def __repr__(self) -> str:
        return f"<PatDocument(id={self.id}, title={self.title}, type={self.document_type})>"
