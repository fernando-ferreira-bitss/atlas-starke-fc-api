"""Cash flow domain entities."""

from datetime import date
from decimal import Decimal
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class CashInCategory(str, Enum):
    """Cash inflow categories."""

    ATIVOS = "ativos"  # Active contracts regular payments
    RECUPERACOES = "recuperacoes"  # Recovery of overdue payments
    ANTECIPACOES = "antecipacoes"  # Advance payments
    OUTRAS = "outras"  # Other inflows (capital injections, etc)


class CashOutCategory(str, Enum):
    """
    Cash outflow categories (DEPRECATED).

    DEPRECATED: These categories are no longer used.
    Cash Out now uses TipoDocumento directly from the API.
    Examples: "NF_REF", "NF SERV", etc.
    """

    OPEX = "opex"  # Operating expenses (DEPRECATED)
    FINANCEIRAS = "financeiras"  # Financial expenses (DEPRECATED)
    CAPEX = "capex"  # Capital expenditures (DEPRECATED)
    DISTRIBUICOES = "distribuicoes"  # Distributions (DEPRECATED)


class CashInData(BaseModel):
    """Cash inflow data."""

    empreendimento_id: int = Field(..., description="Development ID")
    empreendimento_nome: str = Field(..., description="Development name")
    ref_date: date = Field(..., description="Reference date")
    category: CashInCategory = Field(..., description="Inflow category")
    forecast: Decimal = Field(default=Decimal("0"), description="Forecasted amount")
    actual: Decimal = Field(default=Decimal("0"), description="Actual received amount")
    details: dict[str, Any] = Field(default_factory=dict, description="Additional details")

    class Config:
        """Pydantic config."""

        json_encoders = {
            Decimal: lambda v: float(v),
            date: lambda v: v.isoformat(),
        }

    @property
    def variance(self) -> Decimal:
        """Calculate variance (actual - forecast)."""
        return self.actual - self.forecast

    @property
    def variance_pct(self) -> Decimal:
        """Calculate variance percentage."""
        if self.forecast == 0:
            return Decimal("0")
        return (self.variance / self.forecast) * 100


class CashOutData(BaseModel):
    """Cash outflow data."""

    empreendimento_id: int = Field(..., description="Development ID")
    empreendimento_nome: str = Field(..., description="Development name")
    ref_date: date = Field(..., description="Reference date")
    category: str = Field(..., description="Outflow category (TipoDocumento from API, e.g., 'NF_REF', 'NF SERV')")
    budget: Decimal = Field(default=Decimal("0"), description="Budgeted amount")
    actual: Decimal = Field(default=Decimal("0"), description="Actual paid amount")
    details: dict[str, Any] = Field(default_factory=dict, description="Additional details")

    class Config:
        """Pydantic config."""

        json_encoders = {
            Decimal: lambda v: float(v),
            date: lambda v: v.isoformat(),
        }

    @property
    def variance(self) -> Decimal:
        """Calculate variance (actual - budget)."""
        return self.actual - self.budget

    @property
    def variance_pct(self) -> Decimal:
        """Calculate variance percentage."""
        if self.budget == 0:
            return Decimal("0")
        return (self.variance / self.budget) * 100


class BalanceData(BaseModel):
    """Cash balance data."""

    empreendimento_id: int = Field(..., description="Development ID")
    empreendimento_nome: str = Field(..., description="Development name")
    ref_date: date = Field(..., description="Reference date")
    opening: Decimal = Field(default=Decimal("0"), description="Opening balance")
    closing: Decimal = Field(default=Decimal("0"), description="Closing balance")
    total_in: Decimal = Field(default=Decimal("0"), description="Total cash in")
    total_out: Decimal = Field(default=Decimal("0"), description="Total cash out")
    details: dict[str, Any] = Field(default_factory=dict, description="Additional details")

    class Config:
        """Pydantic config."""

        json_encoders = {
            Decimal: lambda v: float(v),
            date: lambda v: v.isoformat(),
        }

    @property
    def net_flow(self) -> Decimal:
        """Calculate net cash flow (in - out)."""
        return self.total_in - self.total_out

    @property
    def variance(self) -> Decimal:
        """Calculate balance variance (closing - opening)."""
        return self.closing - self.opening

    @property
    def variance_pct(self) -> Decimal:
        """Calculate balance variance percentage."""
        if self.opening == 0:
            return Decimal("0")
        return (self.variance / self.opening) * 100


class PortfolioStatsData(BaseModel):
    """Portfolio statistics data."""

    empreendimento_id: int = Field(..., description="Development ID")
    empreendimento_nome: str = Field(..., description="Development name")
    ref_date: date = Field(..., description="Reference date")
    vp: Decimal = Field(default=Decimal("0"), description="Present Value")
    ltv: Decimal = Field(default=Decimal("0"), description="Loan-to-Value ratio")
    prazo_medio: Decimal = Field(default=Decimal("0"), description="Average term (months)")
    duration: Decimal = Field(default=Decimal("0"), description="Duration (months)")
    total_contracts: int = Field(default=0, description="Total number of contracts")
    active_contracts: int = Field(default=0, description="Number of active contracts")
    total_receivable: Decimal = Field(default=Decimal("0"), description="Total receivable amount")
    details: dict[str, Any] = Field(default_factory=dict, description="Additional details")

    class Config:
        """Pydantic config."""

        json_encoders = {
            Decimal: lambda v: float(v),
            date: lambda v: v.isoformat(),
        }

    @property
    def active_ratio(self) -> Decimal:
        """Calculate ratio of active contracts."""
        if self.total_contracts == 0:
            return Decimal("0")
        return (Decimal(self.active_contracts) / Decimal(self.total_contracts)) * 100


class DelinquencyData(BaseModel):
    """Delinquency data by aging buckets."""

    empreendimento_id: int = Field(..., description="Development ID")
    empreendimento_nome: str = Field(..., description="Development name")
    ref_date: date = Field(..., description="Reference date")
    up_to_30: Decimal = Field(default=Decimal("0"), description="0-30 days overdue amount")
    days_30_60: Decimal = Field(default=Decimal("0"), description="30-60 days overdue amount")
    days_60_90: Decimal = Field(default=Decimal("0"), description="60-90 days overdue amount")
    days_90_180: Decimal = Field(default=Decimal("0"), description="90-180 days overdue amount")
    above_180: Decimal = Field(default=Decimal("0"), description=">180 days overdue amount")
    total: Decimal = Field(default=Decimal("0"), description="Total overdue amount")
    details: dict[str, Any] = Field(default_factory=dict, description="Additional details (quantities, breakdown)")

    class Config:
        """Pydantic config."""

        json_encoders = {
            Decimal: lambda v: float(v),
            date: lambda v: v.isoformat(),
        }

    @property
    def total_parcelas(self) -> int:
        """Get total number of overdue parcelas from details."""
        return self.details.get("quantities", {}).get("total", 0)

    @property
    def delinquency_rate(self) -> Decimal:
        """Get delinquency rate from details if available."""
        rate = self.details.get("delinquency_rate", 0)
        return Decimal(str(rate)) if rate else Decimal("0")
