"""Pydantic schemas for assets."""

from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, Field


class AssetBase(BaseModel):
    """Base schema for asset."""

    category: str = Field(
        ...,
        description="Categoria: renda_fixa, renda_variavel, fundos, imoveis, previdencia, outros",
    )
    subcategory: Optional[str] = Field(
        None, max_length=50, description="Subcategoria (ex: CDB, ações, FII)"
    )
    name: str = Field(..., min_length=1, max_length=255, description="Nome do ativo")
    description: Optional[str] = Field(None, description="Descrição")
    ticker: Optional[str] = Field(None, max_length=20, description="Ticker/código")
    base_value: Optional[Decimal] = Field(None, description="Valor de aquisição")
    current_value: Optional[Decimal] = Field(None, description="Valor atual")
    quantity: Optional[Decimal] = Field(None, description="Quantidade")
    base_date: Optional[date] = Field(None, description="Data de aquisição")
    base_year: Optional[int] = Field(None, description="Ano base (para IR)")
    maturity_date: Optional[date] = Field(None, description="Data de vencimento")
    currency: str = Field("BRL", max_length=3, description="Moeda")


class AssetCreate(AssetBase):
    """Schema for creating asset."""

    client_id: str = Field(..., description="ID do cliente")
    account_id: Optional[str] = Field(None, description="ID da conta vinculada")
    document_ids: Optional[list[str]] = Field(None, description="IDs de documentos a vincular")


class AssetUpdate(BaseModel):
    """Schema for updating asset."""

    category: Optional[str] = None
    subcategory: Optional[str] = Field(None, max_length=50)
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    ticker: Optional[str] = Field(None, max_length=20)
    base_value: Optional[Decimal] = None
    current_value: Optional[Decimal] = None
    quantity: Optional[Decimal] = None
    base_date: Optional[date] = None
    base_year: Optional[int] = None
    maturity_date: Optional[date] = None
    currency: Optional[str] = Field(None, max_length=3)
    account_id: Optional[str] = None
    is_active: Optional[bool] = None
    document_ids: Optional[list[str]] = Field(None, description="IDs de documentos a vincular")


class AccountSummary(BaseModel):
    """Account summary for asset response."""

    id: str
    account_type: str
    institution_name: Optional[str] = None


class ClientSummary(BaseModel):
    """Client summary for asset response."""

    id: str
    name: str
    client_type: str


class DocumentSummary(BaseModel):
    """Document summary for asset/liability response."""

    id: str
    title: str
    document_type: str
    file_name: str
    created_at: datetime


class AssetResponse(AssetBase):
    """Schema for asset response."""

    id: str
    client_id: str
    client: Optional[ClientSummary] = None
    account_id: Optional[str]
    account: Optional[AccountSummary] = None
    is_active: bool
    created_at: datetime
    updated_at: Optional[datetime]

    # Computed fields
    gain_loss: Optional[Decimal] = None
    gain_loss_percent: Optional[float] = None

    # Documents
    documents: list[DocumentSummary] = []

    class Config:
        from_attributes = True


class AssetListResponse(BaseModel):
    """Schema for paginated list response."""

    items: list[AssetResponse]
    total: int
    page: int
    per_page: int
    pages: int


class AssetsByCategory(BaseModel):
    """Assets grouped by category."""

    category: str
    total_value: Decimal
    count: int
    percentage: float
    assets: list[AssetResponse]
