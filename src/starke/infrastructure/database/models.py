"""SQLAlchemy database models."""

from datetime import date, datetime
from decimal import Decimal
from enum import Enum as PyEnum
from typing import Any, Optional

from sqlalchemy import JSON, CheckConstraint, ForeignKey, Index, Numeric, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from starke.infrastructure.database.base import Base


class UserRole(str, PyEnum):
    """User roles for authorization."""

    ADMIN = "admin"
    RM = "rm"
    ANALYST = "analyst"
    CLIENT = "client"


class Run(Base):
    """Execution run metadata.

    Each sync creates separate Run records for each source (mega, uau).
    This allows individual tracking of success/failure per source.
    """

    __tablename__ = "runs"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    exec_date: Mapped[str] = mapped_column(String(10), nullable=False, index=True)
    source: Mapped[str] = mapped_column(String(20), nullable=False, default="mega")  # mega, uau
    status: Mapped[str] = mapped_column(String(20), nullable=False)  # pending, running, success, failed
    started_at: Mapped[datetime] = mapped_column(nullable=False, default=datetime.utcnow)
    finished_at: Mapped[Optional[datetime]] = mapped_column(nullable=True)
    error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    metrics: Mapped[Optional[dict[str, Any]]] = mapped_column(JSON, nullable=True)
    triggered_by_user_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )  # NULL = triggered by scheduler

    __table_args__ = (
        Index("idx_exec_date_status", "exec_date", "status"),
        Index("idx_runs_triggered_by", "triggered_by_user_id"),
        Index("idx_runs_source", "source"),
        Index("idx_runs_exec_date_source", "exec_date", "source"),
    )

    def __repr__(self) -> str:
        return f"<Run(id={self.id}, exec_date={self.exec_date}, status={self.status})>"


class RawPayload(Base):
    """Raw API payloads storage for idempotency and audit."""

    __tablename__ = "raw_payloads"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    source: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    exec_date: Mapped[str] = mapped_column(String(10), nullable=False, index=True)
    payload_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    payload_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(nullable=False, default=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("source", "exec_date", "payload_hash", name="uq_payload_idempotency"),
        Index("idx_source_exec_date", "source", "exec_date"),
    )

    def __repr__(self) -> str:
        return f"<RawPayload(id={self.id}, source={self.source}, exec_date={self.exec_date})>"


class CashIn(Base):
    """Cash inflows (recebimentos)."""

    __tablename__ = "entradas_caixa"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    empreendimento_id: Mapped[int] = mapped_column(nullable=False, index=True)
    empreendimento_nome: Mapped[str] = mapped_column(String(200), nullable=False)
    ref_month: Mapped[str] = mapped_column(String(7), nullable=False, index=True)  # YYYY-MM format
    category: Mapped[str] = mapped_column(String(100), nullable=False)  # ativos, recuperacoes, antecipacoes, outras
    forecast: Mapped[float] = mapped_column(nullable=False, default=0.0)
    actual: Mapped[float] = mapped_column(nullable=False, default=0.0)
    details: Mapped[Optional[dict[str, Any]]] = mapped_column(JSON, nullable=True)
    origem: Mapped[str] = mapped_column(String(20), nullable=False, default="mega")  # mega | uau
    created_at: Mapped[datetime] = mapped_column(nullable=False, default=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("empreendimento_id", "ref_month", "category", "origem", name="uq_cash_in_emp_month_category_origem"),
        Index("idx_cash_in_emp_ref_month", "empreendimento_id", "ref_month"),
        Index("idx_cash_in_ref_month_category", "ref_month", "category"),
        Index("idx_cash_in_origem", "origem"),
    )

    def __repr__(self) -> str:
        return f"<CashIn(id={self.id}, emp={self.empreendimento_id}, month={self.ref_month}, category={self.category})>"


class CashOut(Base):
    """Cash outflows (pagamentos) - aggregated by filial."""

    __tablename__ = "saidas_caixa"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    filial_id: Mapped[int] = mapped_column(nullable=False, index=True)  # FK to filiais
    filial_nome: Mapped[str] = mapped_column(String(200), nullable=False)
    mes_referencia: Mapped[str] = mapped_column(String(7), nullable=False, index=True)  # YYYY-MM format
    categoria: Mapped[str] = mapped_column(String(100), nullable=False)  # opex, financeiras, capex, distribuicoes
    orcamento: Mapped[float] = mapped_column(nullable=False, default=0.0)  # budget
    realizado: Mapped[float] = mapped_column(nullable=False, default=0.0)  # actual
    detalhes: Mapped[Optional[dict[str, Any]]] = mapped_column(JSON, nullable=True)
    origem: Mapped[str] = mapped_column(String(20), nullable=False, default="mega")  # mega | uau
    criado_em: Mapped[datetime] = mapped_column(nullable=False, default=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("filial_id", "mes_referencia", "categoria", "origem", name="uq_cash_out_filial_mes_categoria_origem"),
        Index("idx_cash_out_filial_mes_ref", "filial_id", "mes_referencia"),
        Index("idx_cash_out_mes_categoria", "mes_referencia", "categoria"),
        Index("idx_cash_out_origem", "origem"),
    )

    def __repr__(self) -> str:
        return f"<CashOut(id={self.id}, filial={self.filial_id}, mes={self.mes_referencia}, categoria={self.categoria})>"


# NOTE: Balance model removed - saldos table dropped due to data granularity mismatch
# Balance is now calculated dynamically as: cash_in_actual - cash_out_actual


class PortfolioStats(Base):
    """Portfolio statistics (dados de carteira)."""

    __tablename__ = "estatisticas_portfolio"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    empreendimento_id: Mapped[int] = mapped_column(nullable=False, index=True)
    empreendimento_nome: Mapped[str] = mapped_column(String(200), nullable=False)
    ref_month: Mapped[str] = mapped_column(String(7), nullable=False, index=True)  # YYYY-MM format
    vp: Mapped[float] = mapped_column(nullable=False, default=0.0)  # Valor Presente
    ltv: Mapped[float] = mapped_column(nullable=False, default=0.0)  # Loan-to-Value
    prazo_medio: Mapped[float] = mapped_column(nullable=False, default=0.0)  # Average term in months
    duration: Mapped[float] = mapped_column(nullable=False, default=0.0)  # Duration
    total_contracts: Mapped[int] = mapped_column(nullable=False, default=0)
    active_contracts: Mapped[int] = mapped_column(nullable=False, default=0)
    details: Mapped[Optional[dict[str, Any]]] = mapped_column(JSON, nullable=True)
    origem: Mapped[str] = mapped_column(String(20), nullable=False, default="mega")  # mega | uau
    created_at: Mapped[datetime] = mapped_column(nullable=False, default=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("empreendimento_id", "ref_month", "origem", name="uq_portfolio_emp_month_origem"),
        Index("idx_portfolio_emp_ref_month", "empreendimento_id", "ref_month"),
        Index("idx_portfolio_origem", "origem"),
    )

    def __repr__(self) -> str:
        return f"<PortfolioStats(id={self.id}, emp={self.empreendimento_id}, month={self.ref_month}, vp={self.vp})>"


class Delinquency(Base):
    """Delinquency data by aging buckets (dados de inadimplência por faixa)."""

    __tablename__ = "inadimplencia"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    empreendimento_id: Mapped[int] = mapped_column(nullable=False, index=True)
    empreendimento_nome: Mapped[str] = mapped_column(String(200), nullable=False)
    ref_month: Mapped[str] = mapped_column(String(10), nullable=False, index=True)  # YYYY-MM-DD (padronizado)
    up_to_30: Mapped[float] = mapped_column(nullable=False, default=0.0)  # Até 30 dias
    days_30_60: Mapped[float] = mapped_column(nullable=False, default=0.0)  # 30 a 60 dias
    days_60_90: Mapped[float] = mapped_column(nullable=False, default=0.0)  # 60 a 90 dias
    days_90_180: Mapped[float] = mapped_column(nullable=False, default=0.0)  # 90 a 180 dias
    above_180: Mapped[float] = mapped_column(nullable=False, default=0.0)  # Acima de 180 dias
    total: Mapped[float] = mapped_column(nullable=False, default=0.0)  # Total inadimplente
    details: Mapped[Optional[dict[str, Any]]] = mapped_column(JSON, nullable=True)
    origem: Mapped[str] = mapped_column(String(20), nullable=False, default="mega")  # mega | uau
    created_at: Mapped[datetime] = mapped_column(nullable=False, default=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("empreendimento_id", "ref_month", "origem", name="uq_delinquency_emp_date_origem"),
        Index("idx_delinquency_emp_ref_month", "empreendimento_id", "ref_month"),
        Index("idx_delinquency_origem", "origem"),
    )

    def __repr__(self) -> str:
        return f"<Delinquency(id={self.id}, emp={self.empreendimento_id}, month={self.ref_month}, total={self.total})>"


class User(Base):
    """System users with authentication."""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(nullable=False, default=True)
    is_superuser: Mapped[bool] = mapped_column(nullable=False, default=False)  # Mantido para compatibilidade
    role: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default=UserRole.ANALYST.value,
        index=True,
    )
    preferences: Mapped[Optional[dict[str, Any]]] = mapped_column(JSON, nullable=True)  # User preferences
    created_at: Mapped[datetime] = mapped_column(nullable=False, default=datetime.utcnow)
    updated_at: Mapped[Optional[datetime]] = mapped_column(nullable=True, onupdate=datetime.utcnow)

    def __repr__(self) -> str:
        return f"<User(id={self.id}, email={self.email}, role={self.role})>"

    @property
    def is_admin(self) -> bool:
        """Check if user is admin (via role or is_superuser for backward compatibility)."""
        return self.role == UserRole.ADMIN.value or self.is_superuser


class Filial(Base):
    """Filiais (branches) from Mega API or UAU API.

    For Mega: Extracted from empreendimentos data (codigoFilial).
    For UAU: Created from empresas (each empresa = 1 filial).
    Each development belongs to one filial.

    The `external_id` stores the original ID from the API (Mega or UAU).
    The `id` is auto-incremented and used as internal primary key.
    """

    __tablename__ = "filiais"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    external_id: Mapped[int] = mapped_column(nullable=False)  # Original ID from API (codigoFilial for Mega, Codigo_emp for UAU)
    nome: Mapped[str] = mapped_column(String(255), nullable=False)
    fantasia: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    cnpj: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    is_active: Mapped[bool] = mapped_column(nullable=False, default=True)
    origem: Mapped[str] = mapped_column(String(20), nullable=False, default="mega")  # mega | uau
    criado_em: Mapped[datetime] = mapped_column(nullable=False, default=datetime.utcnow)
    atualizado_em: Mapped[Optional[datetime]] = mapped_column(nullable=True, onupdate=datetime.utcnow)

    __table_args__ = (
        Index("idx_filial_origem", "origem"),
        Index("idx_filiais_external_origem", "external_id", "origem", unique=True),
    )

    def __repr__(self) -> str:
        return f"<Filial(id={self.id}, nome={self.nome}, origem={self.origem})>"


class Development(Base):
    """Real estate developments from Mega API or UAU API.

    The `external_id` stores the original ID from the API (Mega or UAU).
    The `id` is auto-incremented and used as internal primary key.
    """

    __tablename__ = "empreendimentos"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    external_id: Mapped[int] = mapped_column(nullable=False)  # Original ID from API (Mega codigo or UAU Codigo_emp)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    filial_id: Mapped[Optional[int]] = mapped_column(nullable=True, index=True)  # FK to filiais (internal id)
    centro_custo_id: Mapped[Optional[int]] = mapped_column(nullable=True, index=True)  # Centro de Custo Reduzido
    is_active: Mapped[bool] = mapped_column(nullable=False, default=True)
    raw_data: Mapped[Optional[dict[str, Any]]] = mapped_column(JSON, nullable=True)  # Full API response
    origem: Mapped[str] = mapped_column(String(20), nullable=False, default="mega")  # mega | uau
    created_at: Mapped[datetime] = mapped_column(nullable=False, default=datetime.utcnow)
    updated_at: Mapped[Optional[datetime]] = mapped_column(nullable=True, onupdate=datetime.utcnow)
    last_synced_at: Mapped[Optional[datetime]] = mapped_column(nullable=True)  # Last sync from API
    last_financial_sync_at: Mapped[Optional[datetime]] = mapped_column(nullable=True)  # Last full financial sync (CashIn/CashOut)

    __table_args__ = (
        Index("idx_development_active", "is_active"),
        Index("idx_development_centro_custo", "centro_custo_id"),
        Index("idx_development_filial", "filial_id"),
        Index("idx_development_origem", "origem"),
        Index("idx_empreendimentos_external_origem", "external_id", "origem", unique=True),
    )

    def __repr__(self) -> str:
        return f"<Development(id={self.id}, name={self.name}, is_active={self.is_active})>"


class Contract(Base):
    """Contracts from Mega/UAU API - used to determine active developments and filter expenses.

    Supports both Mega and UAU data sources via 'origem' field.

    Fields:
    - origem: Data source ('mega' or 'uau')
    - cod_contrato: Contract/Sale ID from API (Mega: cod_contrato, UAU: Numero da Venda)
    - obra: Work code (UAU only, Mega uses NULL)
    - empreendimento_id: Maps contract to development (FK to developments table)
    - status: Used to filter active contracts only
    - valor_contrato: Original contract value
    - valor_atualizado_ipca: Contract value adjusted by IPCA since data_assinatura
    - data_assinatura: Contract signing date (used for IPCA calculation)
    - cliente_cpf: Client CPF/CNPJ (UAU only)
    - cliente_codigo: Client code in UAU system (UAU only)

    UAU StatusVenda mapping:
    - 0 = Normal (Ativo)
    - 1 = Cancelada
    - 2 = Alterada
    - 3 = Quitada
    - 4 = Em acerto

    A development is considered active if it has at least one contract with:
    - status = 'Ativo' or 'Normal'
    - development name (from developments table) does NOT contain 'teste' (case insensitive)
    """

    __tablename__ = "contratos"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    origem: Mapped[str] = mapped_column(String(20), nullable=False, default="mega", index=True)  # 'mega' or 'uau'
    cod_contrato: Mapped[int] = mapped_column(nullable=False, index=True)  # Contract/Sale ID from API
    obra: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)  # UAU: Obra code
    empreendimento_id: Mapped[int] = mapped_column(nullable=False, index=True)  # Development ID
    status: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, index=True)  # Ativo, Cancelado, etc
    valor_contrato: Mapped[Optional[Decimal]] = mapped_column(Numeric(15, 2), nullable=True)  # Original contract value
    valor_atualizado_ipca: Mapped[Optional[Decimal]] = mapped_column(Numeric(15, 2), nullable=True)  # IPCA-adjusted value
    data_assinatura: Mapped[Optional[date]] = mapped_column(nullable=True)  # Contract signing date
    cliente_cpf: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)  # Client CPF/CNPJ (UAU)
    cliente_codigo: Mapped[Optional[int]] = mapped_column(nullable=True)  # Client code (UAU)
    last_synced_at: Mapped[Optional[datetime]] = mapped_column(nullable=True)  # Last sync from API

    __table_args__ = (
        UniqueConstraint("cod_contrato", "empreendimento_id", "obra", "origem", name="uq_contract_cod_emp_origem"),
        Index("idx_contract_emp_status", "empreendimento_id", "status"),
        Index("idx_contract_status", "status"),
        Index("idx_contract_origem", "origem"),
    )

    def __repr__(self) -> str:
        return f"<Contract(id={self.id}, cod={self.cod_contrato}, emp={self.empreendimento_id}, status={self.status}, origem={self.origem})>"

    @property
    def is_active(self) -> bool:
        """Check if contract is active."""
        if not self.status:
            return False
        status_lower = self.status.lower()
        return status_lower in ("ativo", "normal")


class FaturaPagar(Base):
    """Faturas a pagar from Mega/UAU API - individual invoices to pay.

    Supports both Mega and UAU data sources via 'origem' field.

    Fields:
    - origem: Data source ('mega' or 'uau')
    - filial_id: Branch ID from API
    - numero_ap: Invoice number (AP = Accounts Payable)
    - numero_parcela: Installment number
    - tipo_documento: Document type (DISTRATO, NOTA FISCAL, BOLETO, etc)
    - valor_parcela: Original installment value
    - saldo_atual: Current balance (0 if paid)
    - data_vencimento: Due date
    - data_baixa: Payment date (set when saldo goes from >0 to 0)

    Logic for data_baixa:
    - If invoice existed in DB with saldo > 0 and now saldo = 0 → use current date
    - If invoice didn't exist in DB and saldo = 0 → use data_vencimento
    - Otherwise → NULL

    For UAU desembolsos:
    - numero_ap: Composite key (Empresa-Obra-Contrato-Produto-Composicao-Item)
    - numero_parcela: DtaRef formatted as YYYYMM
    - tipo_documento: Composicao or Item description
    - saldo_atual: 0 if Status='Pago', else valor_parcela
    """

    __tablename__ = "faturas_pagar"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    origem: Mapped[str] = mapped_column(String(10), nullable=False, default="mega", index=True)
    filial_id: Mapped[int] = mapped_column(nullable=False, index=True)
    filial_nome: Mapped[str] = mapped_column(String(255), nullable=False)
    numero_ap: Mapped[str] = mapped_column(String(100), nullable=False)
    numero_parcela: Mapped[str] = mapped_column(String(50), nullable=False)
    tipo_documento: Mapped[str] = mapped_column(String(100), nullable=False)
    numero_documento: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    valor_parcela: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False)
    saldo_atual: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False)
    data_vencimento: Mapped[date] = mapped_column(nullable=False, index=True)
    data_baixa: Mapped[Optional[date]] = mapped_column(nullable=True, index=True)
    agente_codigo: Mapped[Optional[int]] = mapped_column(nullable=True)
    agente_nome: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    dados_brutos: Mapped[Optional[dict[str, Any]]] = mapped_column(JSON, nullable=True)
    criado_em: Mapped[datetime] = mapped_column(nullable=False, default=datetime.utcnow)
    atualizado_em: Mapped[datetime] = mapped_column(nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("origem", "filial_id", "numero_ap", "numero_parcela", name="uq_fatura_origem_filial_ap_parcela"),
        Index("idx_fatura_filial_vencimento", "filial_id", "data_vencimento"),
        Index("idx_fatura_filial_baixa", "filial_id", "data_baixa"),
        Index("idx_fatura_tipo_documento", "tipo_documento"),
        Index("idx_fatura_origem", "origem"),
    )

    def __repr__(self) -> str:
        return f"<FaturaPagar(id={self.id}, ap={self.numero_ap}, parcela={self.numero_parcela}, filial={self.filial_id}, saldo={self.saldo_atual})>"

    @property
    def esta_pago(self) -> bool:
        """Check if invoice is paid (saldo = 0)."""
        return self.saldo_atual == 0


# =============================================================================
# Permission System Models
# =============================================================================


class RolePermission(Base):
    """Permissions by role and screen.

    Stores which screens/modules each role has access to.
    If a role has a permission for a screen, users with that role can access it.
    """

    __tablename__ = "role_permissions"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    role: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    screen_code: Mapped[str] = mapped_column(String(100), nullable=False)
    created_at: Mapped[datetime] = mapped_column(nullable=False, default=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("role", "screen_code", name="uq_role_screen"),
        CheckConstraint(
            "role IN ('admin', 'rm', 'analyst', 'client')",
            name="check_role_permissions_role",
        ),
        Index("idx_role_permissions_role", "role"),
        Index("idx_role_permissions_screen", "screen_code"),
    )

    def __repr__(self) -> str:
        return f"<RolePermission(role={self.role}, screen={self.screen_code})>"


class ImpersonationLog(Base):
    """Log de sessões de impersonation.

    Registra quando um admin/rm visualiza o portal como um cliente.
    Usado para auditoria e rastreabilidade.
    """

    __tablename__ = "impersonation_logs"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    actor_user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    target_client_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    target_user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    started_at: Mapped[datetime] = mapped_column(nullable=False, default=datetime.utcnow)
    ended_at: Mapped[Optional[datetime]] = mapped_column(nullable=True)

    __table_args__ = (
        Index("idx_impersonation_actor", "actor_user_id"),
        Index("idx_impersonation_target", "target_client_id"),
        Index("idx_impersonation_started", "started_at"),
    )

    def __repr__(self) -> str:
        return f"<ImpersonationLog(id={self.id}, actor={self.actor_user_id}, target_client={self.target_client_id})>"
