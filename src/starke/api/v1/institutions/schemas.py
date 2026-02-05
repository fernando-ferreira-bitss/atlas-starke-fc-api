"""Pydantic schemas for institutions."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class InstitutionBase(BaseModel):
    """Base schema for institution."""

    name: str = Field(..., min_length=1, max_length=255, description="Nome da instituição")
    code: Optional[str] = Field(None, max_length=50, description="Código da instituição")
    institution_type: str = Field(
        "bank",
        description="Tipo: bank, broker, insurance, pension, other",
    )


class InstitutionCreate(InstitutionBase):
    """Schema for creating institution."""

    code: str = Field(..., min_length=1, max_length=50, description="Código da instituição")


class InstitutionUpdate(BaseModel):
    """Schema for updating institution."""

    name: Optional[str] = Field(None, min_length=1, max_length=255)
    code: Optional[str] = Field(None, max_length=50)
    institution_type: Optional[str] = None
    is_active: Optional[bool] = None


class InstitutionResponse(InstitutionBase):
    """Schema for institution response."""

    id: str
    is_active: bool
    created_at: datetime
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True


class InstitutionListResponse(BaseModel):
    """Schema for paginated list response."""

    items: list[InstitutionResponse]
    total: int
    page: int
    per_page: int
    pages: int
