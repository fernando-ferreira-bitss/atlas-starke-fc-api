"""Pydantic schemas for accounts."""

from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, Field


class AccountBase(BaseModel):
    """Base schema for account."""

    account_type: str = Field(
        ..., description="Tipo: checking, savings, investment, credit_card, other"
    )
    account_number: Optional[str] = Field(None, max_length=50, description="Número da conta")
    agency: Optional[str] = Field(None, max_length=20, description="Agência")
    currency: str = Field("BRL", max_length=3, description="Moeda")
    base_date: Optional[date] = Field(None, description="Data base")
    notes: Optional[str] = Field(None, description="Observações")


class AccountCreate(AccountBase):
    """Schema for creating account."""

    client_id: str = Field(..., description="ID do cliente")
    institution_id: Optional[str] = Field(None, description="ID da instituição")


class AccountUpdate(BaseModel):
    """Schema for updating account."""

    account_type: Optional[str] = None
    account_number: Optional[str] = Field(None, max_length=50)
    agency: Optional[str] = Field(None, max_length=20)
    currency: Optional[str] = Field(None, max_length=3)
    base_date: Optional[date] = None
    notes: Optional[str] = None
    institution_id: Optional[str] = None
    is_active: Optional[bool] = None


class InstitutionSummary(BaseModel):
    """Institution summary for account response."""

    id: str
    name: str
    code: Optional[str]


class ClientSummary(BaseModel):
    """Client summary for account response."""

    id: str
    name: str
    client_type: str


class AccountResponse(AccountBase):
    """Schema for account response."""

    id: str
    client_id: str
    client: Optional[ClientSummary] = None
    institution_id: Optional[str]
    institution: Optional[InstitutionSummary] = None
    is_active: bool
    created_at: datetime
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True


class AccountListResponse(BaseModel):
    """Schema for paginated list response."""

    items: list[AccountResponse]
    total: int
    page: int
    per_page: int
    pages: int
