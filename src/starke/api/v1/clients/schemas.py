"""Pydantic schemas for clients."""

from datetime import datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, Field, field_validator
import re


def validate_cpf_cnpj(value: str) -> str:
    """Validate CPF or CNPJ format."""
    # Remove formatting
    digits = re.sub(r"[^\d]", "", value)

    if len(digits) == 11:
        # CPF validation
        if not _validate_cpf(digits):
            raise ValueError("CPF inválido")
    elif len(digits) == 14:
        # CNPJ validation
        if not _validate_cnpj(digits):
            raise ValueError("CNPJ inválido")
    else:
        raise ValueError("CPF deve ter 11 dígitos ou CNPJ deve ter 14 dígitos")

    return value


def _validate_cpf(cpf: str) -> bool:
    """Validate CPF digits."""
    if len(cpf) != 11 or cpf == cpf[0] * 11:
        return False

    # First digit
    soma = sum(int(cpf[i]) * (10 - i) for i in range(9))
    resto = soma % 11
    d1 = 0 if resto < 2 else 11 - resto
    if int(cpf[9]) != d1:
        return False

    # Second digit
    soma = sum(int(cpf[i]) * (11 - i) for i in range(10))
    resto = soma % 11
    d2 = 0 if resto < 2 else 11 - resto
    if int(cpf[10]) != d2:
        return False

    return True


def _validate_cnpj(cnpj: str) -> bool:
    """Validate CNPJ digits."""
    if len(cnpj) != 14 or cnpj == cnpj[0] * 14:
        return False

    # First digit
    pesos1 = [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
    soma = sum(int(cnpj[i]) * pesos1[i] for i in range(12))
    resto = soma % 11
    d1 = 0 if resto < 2 else 11 - resto
    if int(cnpj[12]) != d1:
        return False

    # Second digit
    pesos2 = [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
    soma = sum(int(cnpj[i]) * pesos2[i] for i in range(13))
    resto = soma % 11
    d2 = 0 if resto < 2 else 11 - resto
    if int(cnpj[13]) != d2:
        return False

    return True


class ClientBase(BaseModel):
    """Base schema for client."""

    name: str = Field(..., min_length=1, max_length=255, description="Nome do cliente")
    client_type: str = Field(..., description="Tipo: pf, pj, family ou company")
    email: Optional[str] = Field(None, max_length=255, description="Email")
    phone: Optional[str] = Field(None, max_length=20, description="Telefone")
    base_currency: str = Field("BRL", max_length=3, description="Moeda base")
    notes: Optional[str] = Field(None, description="Observações")


class CreateLoginData(BaseModel):
    """Data for creating user login along with client."""

    password: str = Field(..., min_length=6, max_length=100, description="Senha do usuário")


class ClientCreate(ClientBase):
    """Schema for creating client."""

    cpf_cnpj: str = Field(..., description="CPF ou CNPJ")
    rm_user_id: Optional[int] = Field(None, description="ID do RM responsável")
    status: str = Field("active", description="Status: active, inactive, pending")
    create_login: Optional[CreateLoginData] = Field(
        None,
        description="Se informado, cria usuário com role=client vinculado ao cliente. Requer email preenchido."
    )

    @field_validator("cpf_cnpj")
    @classmethod
    def validate_cpf_cnpj_field(cls, v: str) -> str:
        return validate_cpf_cnpj(v)


class ClientUpdate(BaseModel):
    """Schema for updating client."""

    name: Optional[str] = Field(None, min_length=1, max_length=255)
    email: Optional[str] = Field(None, max_length=255)
    phone: Optional[str] = Field(None, max_length=20)
    base_currency: Optional[str] = Field(None, max_length=3)
    notes: Optional[str] = None
    status: Optional[str] = None
    rm_user_id: Optional[int] = None


class ClientResponse(ClientBase):
    """Schema for client response."""

    id: str
    cpf_cnpj: str = Field(..., description="CPF ou CNPJ")
    status: str
    rm_user_id: Optional[int]
    rm_user_name: Optional[str] = None
    user_id: Optional[int] = None
    user_email: Optional[str] = None
    has_login: bool = False
    created_at: datetime
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True


class ClientDetailResponse(ClientResponse):
    """Detailed client response with summary."""

    total_assets: Decimal = Field(default=Decimal("0"))
    total_liabilities: Decimal = Field(default=Decimal("0"))
    net_worth: Decimal = Field(default=Decimal("0"))
    accounts_count: int = 0
    assets_count: int = 0
    liabilities_count: int = 0


class ClientListResponse(BaseModel):
    """Schema for paginated list response."""

    items: list[ClientResponse]
    total: int
    page: int
    per_page: int
    pages: int


class ClientSummaryResponse(BaseModel):
    """Summary of client's patrimony."""

    client_id: str
    client_name: str
    total_assets: Decimal
    total_liabilities: Decimal
    net_worth: Decimal
    assets_by_category: dict[str, Decimal]
    liabilities_by_type: dict[str, Decimal]
    accounts_count: int
    assets_count: int
    liabilities_count: int
