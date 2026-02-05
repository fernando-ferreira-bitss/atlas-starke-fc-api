"""Schemas for Reports API."""

from datetime import date
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class CategoryBreakdown(BaseModel):
    """Category breakdown for cash flow."""
    category: str
    forecast: float = 0
    actual: float = 0
    budget: float = 0


class TopCategory(BaseModel):
    """Top category with name and value."""
    name: str
    value: float


class CashFlowPortfolioStats(BaseModel):
    """Portfolio stats for cash flow report."""
    vp: float = Field(0, description="Valor Presente")
    ltv: float = Field(0, description="Loan-to-Value (%)")
    prazo_medio: float = Field(0, description="Prazo Médio (meses)")
    duration: float = Field(0, description="Duration Macaulay")


class CashFlowResponse(BaseModel):
    """Cash flow report response."""
    filial_id: Optional[int] = None
    filial_name: str
    is_consolidated: bool
    start_date: str
    end_date: str

    # Totals
    total_cash_in: float
    total_cash_in_forecast: float
    total_cash_out: float
    total_cash_out_budget: float

    # Balance
    balance_opening: float
    balance_closing: float

    # Variance
    cash_in_variance: float
    cash_in_variance_pct: float
    cash_out_variance: float
    cash_out_variance_pct: float

    # Breakdown by category
    cash_in_by_category: List[CategoryBreakdown]
    cash_out_by_category: List[CategoryBreakdown]

    # Additional metrics for dashboard
    immediate_liquidity_months: float = Field(0, description="Liquidez imediata em meses")
    top_cash_in_category: Optional[TopCategory] = None
    top_cash_out_category: Optional[TopCategory] = None
    portfolio_stats: Optional[CashFlowPortfolioStats] = None


class PortfolioStatsData(BaseModel):
    """Portfolio statistics."""
    vp: float = Field(description="Valor Presente")
    ltv: float = Field(description="Loan-to-Value (%)")
    prazo_medio: float = Field(description="Prazo Médio (meses)")
    duration: float = Field(description="Duration Macaulay")
    total_contracts: int
    active_contracts: int
    total_receipts: float
    avg_monthly_receipts: float
    forecast_vs_actual_pct: float


class TemporalYieldData(BaseModel):
    """Monthly yield data."""
    month: str
    receipts_total: float
    deductions: float
    net_receipts: float
    vp: float
    yield_pct: float


class DelinquencyData(BaseModel):
    """Monthly delinquency data."""
    month: str
    up_to_30: float
    days_30_60: float
    days_60_90: float
    days_90_180: float
    above_180: float
    total: float
    qty_up_to_30: int = 0
    qty_days_30_60: int = 0
    qty_days_60_90: int = 0
    qty_days_90_180: int = 0
    qty_above_180: int = 0
    qty_total: int = 0


class PortfolioPerformanceResponse(BaseModel):
    """Portfolio performance report response."""
    portfolio_stats: PortfolioStatsData
    temporal_yield_data: List[TemporalYieldData]
    delinquency_data: List[DelinquencyData]


class EvolutionDataItem(BaseModel):
    """Monthly evolution data item."""
    month_year: str
    cash_in: float
    cash_out: float
    net_flow: float
    vp: float
    yield_mensal: float


class EvolutionDataResponse(BaseModel):
    """Evolution data response."""
    success: bool = True
    data: List[EvolutionDataItem]
    period: Dict[str, Any]


class DevelopmentItem(BaseModel):
    """Development/Filial item for dropdown."""
    id: int
    name: str
    is_active: bool = True


class FilialItem(BaseModel):
    """Filial item for dropdown."""
    id: int
    nome: str
    is_active: bool = True


class DevelopmentsListResponse(BaseModel):
    """Response with developments and filials for report filters."""
    developments: List[DevelopmentItem]
    filiais: List[FilialItem]
