"""Position schemas."""

from datetime import date, datetime
from decimal import Decimal
from typing import Optional
from pydantic import BaseModel, ConfigDict


class PositionAssetItem(BaseModel):
    """Asset item in position snapshot."""

    asset_id: str
    name: str
    category: str
    value: Decimal
    quantity: Optional[Decimal] = None
    currency: str = "BRL"


class PositionCategoryDetail(BaseModel):
    """Category detail in position snapshot."""

    total: Decimal
    items: list[PositionAssetItem]


class PositionLiabilityItem(BaseModel):
    """Liability item in position snapshot."""

    liability_id: str
    description: str
    value: Decimal
    currency: str = "BRL"


class PositionSnapshot(BaseModel):
    """Full position snapshot structure."""

    assets_by_category: dict[str, PositionCategoryDetail]
    liabilities: dict  # {total: Decimal, items: list}


class PositionCreate(BaseModel):
    """Schema for creating a position snapshot."""

    client_id: str
    reference_date: date  # Should be last day of month


class PositionGenerateAll(BaseModel):
    """Schema for generating all positions."""

    reference_date: date  # Should be last day of month
    overwrite: bool = False


class PositionResponse(BaseModel):
    """Position response schema."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    client_id: str
    client_name: Optional[str] = None
    reference_date: date
    total_assets: Decimal
    total_liabilities: Decimal
    net_worth: Decimal
    status: str = "processed"  # processed, pending, error
    snapshot: Optional[dict] = None
    created_at: datetime
    updated_at: Optional[datetime] = None


class PositionListResponse(BaseModel):
    """Paginated position list response."""

    items: list[PositionResponse]
    total: int
    page: int
    per_page: int
    pages: int


class PositionGenerateAllResponse(BaseModel):
    """Response for generate all positions."""

    total_clients: int
    total_generated: int
    total_skipped: int
    errors: list[dict]


# New schemas for position items and import endpoints

class PositionItemResponse(BaseModel):
    """Individual position item response."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    reference_date: date
    client_id: str
    client_name: Optional[str] = None
    asset_name: str
    value: Decimal
    currency: str = "BRL"
    source: str = "manual"


class PositionItemListResponse(BaseModel):
    """Paginated position items list response."""

    items: list[PositionItemResponse]
    total: int
    page: int
    per_page: int
    pages: int


class ImportError(BaseModel):
    """Import error detail."""

    row: int
    field: Optional[str] = None
    message: str


class PositionImportResponse(BaseModel):
    """Response for position import."""

    success: bool
    imported_count: int
    errors: list[ImportError]
    created_at: datetime


class PositionValidateResponse(BaseModel):
    """Response for position validation."""

    total_items: int
    valid_count: int
    invalid_count: int
    errors: list[ImportError]


class ImportHistoryItem(BaseModel):
    """Import history item."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    file_name: str
    reference_date: str
    imported_count: int
    status: str
    uploaded_by: Optional[str] = None
    created_at: datetime


class ImportHistoryListResponse(BaseModel):
    """Paginated import history list response."""

    items: list[ImportHistoryItem]
    total: int
    page: int
    per_page: int
    pages: int
