"""Pydantic schemas for liabilities."""

from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, Field


class LiabilityBase(BaseModel):
    """Base schema for liability."""

    liability_type: str = Field(
        ...,
        description="Tipo: mortgage, vehicle_loan, personal_loan, credit_card, overdraft, other",
    )
    description: str = Field(..., min_length=1, max_length=255, description="Descrição")
    notes: Optional[str] = Field(None, description="Observações")
    original_amount: Decimal = Field(..., description="Valor original")
    current_balance: Decimal = Field(..., description="Saldo devedor atual")
    monthly_payment: Optional[Decimal] = Field(None, description="Parcela mensal")
    interest_rate: Optional[Decimal] = Field(None, description="Taxa de juros anual (%)")
    start_date: Optional[date] = Field(None, description="Data de contratação")
    end_date: Optional[date] = Field(None, description="Data prevista de quitação")
    last_payment_date: Optional[date] = Field(None, description="Data do último pagamento")
    currency: str = Field("BRL", max_length=3, description="Moeda")


class LiabilityCreate(LiabilityBase):
    """Schema for creating liability."""

    client_id: str = Field(..., description="ID do cliente")
    institution_id: Optional[str] = Field(None, description="ID da instituição credora")
    document_ids: Optional[list[str]] = Field(None, description="IDs de documentos a vincular")


class LiabilityUpdate(BaseModel):
    """Schema for updating liability."""

    liability_type: Optional[str] = None
    description: Optional[str] = Field(None, min_length=1, max_length=255)
    notes: Optional[str] = None
    original_amount: Optional[Decimal] = None
    current_balance: Optional[Decimal] = None
    monthly_payment: Optional[Decimal] = None
    interest_rate: Optional[Decimal] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    last_payment_date: Optional[date] = None
    currency: Optional[str] = Field(None, max_length=3)
    institution_id: Optional[str] = None
    is_active: Optional[bool] = None
    document_ids: Optional[list[str]] = Field(None, description="IDs de documentos a vincular")


class InstitutionSummary(BaseModel):
    """Institution summary for liability response."""

    id: str
    name: str
    code: Optional[str]


class DocumentSummary(BaseModel):
    """Document summary for liability response."""

    id: str
    title: str
    document_type: str
    file_name: str
    created_at: datetime


class LiabilityResponse(LiabilityBase):
    """Schema for liability response."""

    id: str
    client_id: str
    institution_id: Optional[str]
    institution: Optional[InstitutionSummary] = None
    is_active: bool
    is_paid_off: bool = False
    created_at: datetime
    updated_at: Optional[datetime]

    # Computed fields
    remaining_payments: Optional[int] = None
    total_to_pay: Optional[Decimal] = None

    # Documents
    documents: list[DocumentSummary] = []

    class Config:
        from_attributes = True


class LiabilityListResponse(BaseModel):
    """Schema for paginated list response."""

    items: list[LiabilityResponse]
    total: int
    page: int
    per_page: int
    pages: int


class LiabilitiesByType(BaseModel):
    """Liabilities grouped by type."""

    liability_type: str
    total_balance: Decimal
    total_monthly_payment: Decimal
    count: int
    percentage: float
    liabilities: list[LiabilityResponse]
