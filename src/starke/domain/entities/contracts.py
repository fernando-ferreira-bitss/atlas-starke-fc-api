"""Contract domain entities."""

from datetime import date, datetime
from decimal import Decimal
from typing import Any, Optional

from pydantic import BaseModel, Field, field_validator


class ContratoData(BaseModel):
    """Contract data from Mega API."""

    codigo_contrato: int = Field(..., description="Contract ID")
    codigo_empreendimento: int = Field(..., description="Empreendimento ID")
    cpf_cnpj: Optional[str] = Field(None, description="Customer CPF/CNPJ")
    nome_cliente: Optional[str] = Field(None, description="Customer name")
    valor_contrato: Decimal = Field(default=Decimal("0"), description="Contract value")
    data_contrato: Optional[date] = Field(None, description="Contract date")
    status: Optional[str] = Field(None, description="Contract status")
    numero_parcelas: int = Field(default=0, description="Number of installments")
    valor_entrada: Decimal = Field(default=Decimal("0"), description="Down payment")
    saldo_devedor: Decimal = Field(default=Decimal("0"), description="Outstanding balance")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Additional metadata")

    class Config:
        """Pydantic config."""

        json_encoders = {
            Decimal: lambda v: float(v),
            date: lambda v: v.isoformat(),
        }

    @field_validator("cpf_cnpj", mode="before")
    @classmethod
    def normalize_cpf_cnpj(cls, v: Optional[str]) -> Optional[str]:
        """Remove formatting from CPF/CNPJ."""
        if not v:
            return v
        return "".join(filter(str.isdigit, v))


class ParcelaData(BaseModel):
    """Installment data from Mega API."""

    codigo_parcela: int = Field(..., description="Installment ID")
    codigo_contrato: int = Field(..., description="Contract ID")
    numero_parcela: int = Field(..., description="Installment number")
    data_vencimento: date = Field(..., description="Due date")
    data_pagamento: Optional[date] = Field(None, description="Payment date")
    valor_parcela: Decimal = Field(..., description="Installment value")
    valor_pago: Decimal = Field(default=Decimal("0"), description="Amount paid")
    juros: Decimal = Field(default=Decimal("0"), description="Interest")
    multa: Decimal = Field(default=Decimal("0"), description="Fine")
    desconto: Decimal = Field(default=Decimal("0"), description="Discount")
    status: str = Field(..., description="Status (pago, aberto, vencido, etc)")
    tipo: Optional[str] = Field(None, description="Type (normal, antecipacao, renegociacao)")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Additional metadata")

    class Config:
        """Pydantic config."""

        json_encoders = {
            Decimal: lambda v: float(v),
            date: lambda v: v.isoformat(),
        }

    @property
    def is_paid(self) -> bool:
        """Check if installment is paid."""
        return self.status.lower() in ("pago", "liquidado", "quitado")

    @property
    def is_overdue(self) -> bool:
        """Check if installment is overdue."""
        if self.is_paid:
            return False
        return self.data_vencimento < date.today()

    @property
    def valor_total(self) -> Decimal:
        """Calculate total amount (value + interest + fine - discount)."""
        return self.valor_parcela + self.juros + self.multa - self.desconto
