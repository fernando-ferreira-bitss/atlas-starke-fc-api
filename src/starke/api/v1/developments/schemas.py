"""Pydantic schemas for developments (empreendimentos)."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class DevelopmentResponse(BaseModel):
    """Schema for development response."""

    id: int
    external_id: int = Field(..., description="ID original no sistema de origem (Mega ou UAU)")
    name: str = Field(..., description="Nome do empreendimento")
    filial_id: Optional[int] = Field(None, description="ID da filial associada")
    centro_custo_id: Optional[int] = Field(None, description="ID do centro de custo")
    is_active: bool = Field(..., description="Se o empreendimento está ativo para sincronização")
    origem: str = Field(..., description="Sistema de origem: mega ou uau")
    created_at: datetime
    updated_at: Optional[datetime]
    last_synced_at: Optional[datetime] = Field(None, description="Data da última sincronização")

    class Config:
        from_attributes = True


class DevelopmentListResponse(BaseModel):
    """Schema for paginated list response."""

    items: list[DevelopmentResponse]
    total: int
    page: int
    per_page: int
    pages: int


class DevelopmentActivateResponse(BaseModel):
    """Schema for activation/deactivation response."""

    id: int
    name: str
    is_active: bool
    filial_id: Optional[int]
    filial_is_active: Optional[bool] = Field(None, description="Status da filial após a operação")
    message: str
