"""Reports API routes - JSON endpoints."""

from collections import defaultdict
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from starke.api.dependencies import get_current_active_user, get_db
from starke.core.date_helpers import get_months_between, normalize_ref_date
from starke.infrastructure.database.models import (
    CashIn,
    CashOut,
    Delinquency,
    Development,
    Filial,
    PortfolioStats,
    User,
)

from .schemas import (
    CashFlowPortfolioStats,
    CashFlowResponse,
    CategoryBreakdown,
    DelinquencyData,
    DevelopmentItem,
    DevelopmentsListResponse,
    EvolutionDataItem,
    EvolutionDataResponse,
    FilialItem,
    PortfolioPerformanceResponse,
    PortfolioStatsData,
    TemporalYieldData,
    TopCategory,
)

router = APIRouter(prefix="/reports", tags=["Reports"])


def _validate_origem(origem: Optional[str]) -> Optional[str]:
    """Valida e retorna origem normalizada.

    Aceita tanto valores técnicos (mega, uau) quanto nomes de exibição (ABecker, JVF).
    Retorna sempre o valor normalizado (mega ou uau).
    """
    if origem is None:
        return None
    origem_lower = origem.lower()
    # Mapeia nomes de exibição para valores técnicos
    display_name_mapping = {
        "abecker": "mega",
        "jvf": "uau",
    }
    if origem_lower in display_name_mapping:
        return display_name_mapping[origem_lower]
    if origem_lower in ["mega", "uau"]:
        return origem_lower
    raise HTTPException(
        status_code=400,
        detail="origem deve ser 'mega', 'uau', 'ABecker' ou 'JVF'"
    )


def _parse_date(date_str: str) -> date:
    """Parse date string in YYYY-MM-DD or YYYY-MM format."""
    if len(date_str) == 7:  # YYYY-MM format
        date_str = f"{date_str}-01"
    return datetime.fromisoformat(date_str).date()


@router.get("/developments", response_model=DevelopmentsListResponse)
def get_developments_list(
    active_only: bool = Query(True, description="Retornar apenas ativos"),
    origem: Optional[str] = Query(None, description="Filtrar por origem: mega ou uau"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> DevelopmentsListResponse:
    """
    Retorna lista de empreendimentos e filiais para filtros de relatórios.

    - **active_only**: Se True, retorna apenas empreendimentos/filiais ativos
    - **origem**: Filtrar por origem (mega = ABecker, uau = JVF)
    """
    origem = _validate_origem(origem)

    # Get developments
    dev_query = db.query(Development)
    if active_only:
        dev_query = dev_query.filter(Development.is_active == True)
    if origem:
        dev_query = dev_query.filter(Development.origem == origem)
    developments = dev_query.order_by(Development.name).all()

    # Get filiais
    filial_query = db.query(Filial)
    if active_only:
        filial_query = filial_query.filter(Filial.is_active == True)
    if origem:
        filial_query = filial_query.filter(Filial.origem == origem)
    filiais = filial_query.order_by(Filial.nome).all()

    # Get max last_financial_sync_at per filial from developments
    last_sync_query = (
        db.query(
            Development.filial_id,
            func.max(Development.last_financial_sync_at).label("last_financial_sync_at")
        )
        .filter(Development.filial_id.isnot(None))
        .group_by(Development.filial_id)
    )
    if active_only:
        last_sync_query = last_sync_query.filter(Development.is_active == True)
    if origem:
        last_sync_query = last_sync_query.filter(Development.origem == origem)
    last_sync_by_filial = {row.filial_id: row.last_financial_sync_at for row in last_sync_query.all()}

    return DevelopmentsListResponse(
        developments=[
            DevelopmentItem(
                id=d.id,
                name=d.name,
                is_active=d.is_active,
                origem=d.origem,
                last_financial_sync_at=d.last_financial_sync_at,
            )
            for d in developments
        ],
        filiais=[
            FilialItem(
                id=f.id,
                nome=f.nome,
                is_active=f.is_active,
                origem=f.origem,
                last_financial_sync_at=last_sync_by_filial.get(f.id),
            )
            for f in filiais
        ],
    )


@router.get("/cash-flow", response_model=CashFlowResponse)
def get_cash_flow(
    start_date: str = Query(..., description="Data inicial (YYYY-MM-DD ou YYYY-MM)"),
    end_date: Optional[str] = Query(None, description="Data final (YYYY-MM-DD ou YYYY-MM)"),
    filial_id: Optional[int] = Query(None, description="ID da filial (omitir para consolidado)"),
    origem: Optional[str] = Query(None, description="Filtrar por origem: mega ou uau"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> CashFlowResponse:
    """
    Retorna dados de fluxo de caixa.

    - **start_date**: Data inicial do período
    - **end_date**: Data final do período (default: start_date)
    - **filial_id**: Filtrar por filial específica (omitir para visão consolidada)
    - **origem**: Filtrar por origem (mega = ABecker, uau = JVF)
    """
    origem = _validate_origem(origem)
    try:
        start = normalize_ref_date(_parse_date(start_date))
        end = normalize_ref_date(_parse_date(end_date)) if end_date else start
        period_dates = get_months_between(start, end)
        month_strings = [d.strftime("%Y-%m") for d in period_dates]
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Formato de data inválido: {str(e)}")

    is_consolidated = filial_id is None

    if is_consolidated:
        # Consolidated view: aggregate across all active filiais
        cash_out_query = (
            db.query(CashOut)
            .join(Filial, CashOut.filial_id == Filial.id)
            .filter(Filial.is_active == True, CashOut.mes_referencia.in_(month_strings))
        )
        if origem:
            cash_out_query = cash_out_query.filter(CashOut.origem == origem)
        all_cash_out = cash_out_query.all()

        cash_in_query = (
            db.query(CashIn)
            .join(Development, CashIn.empreendimento_id == Development.id)
            .join(Filial, Development.filial_id == Filial.id)
            .filter(Filial.is_active == True, CashIn.ref_month.in_(month_strings))
        )
        if origem:
            cash_in_query = cash_in_query.filter(CashIn.origem == origem)
        all_cash_in = cash_in_query.all()

        filial_name = "Consolidado"
    else:
        filial = (
            db.query(Filial)
            .filter(Filial.id == filial_id, Filial.is_active == True)
            .first()
        )
        if not filial:
            raise HTTPException(status_code=404, detail="Filial não encontrada")

        filial_name = filial.nome

        cash_out_query = (
            db.query(CashOut)
            .filter(CashOut.filial_id == filial_id, CashOut.mes_referencia.in_(month_strings))
        )
        if origem:
            cash_out_query = cash_out_query.filter(CashOut.origem == origem)
        all_cash_out = cash_out_query.all()

        cash_in_query = (
            db.query(CashIn)
            .join(Development, CashIn.empreendimento_id == Development.id)
            .filter(Development.filial_id == filial_id, CashIn.ref_month.in_(month_strings))
        )
        if origem:
            cash_in_query = cash_in_query.filter(CashIn.origem == origem)
        all_cash_in = cash_in_query.all()

    # Aggregate data
    total_cash_in_by_category = defaultdict(lambda: {"forecast": Decimal("0"), "actual": Decimal("0")})
    total_cash_out_by_category = defaultdict(lambda: {"budget": Decimal("0"), "actual": Decimal("0")})

    for r in all_cash_in:
        total_cash_in_by_category[r.category]["forecast"] += Decimal(str(r.forecast))
        total_cash_in_by_category[r.category]["actual"] += Decimal(str(r.actual))

    for r in all_cash_out:
        total_cash_out_by_category[r.categoria]["budget"] += Decimal(str(r.orcamento))
        total_cash_out_by_category[r.categoria]["actual"] += Decimal(str(r.realizado))

    # Calculate totals
    total_cash_in_forecast = sum(v["forecast"] for v in total_cash_in_by_category.values())
    total_cash_in_actual = sum(v["actual"] for v in total_cash_in_by_category.values())
    total_cash_out_budget = sum(v["budget"] for v in total_cash_out_by_category.values())
    total_cash_out_actual = sum(v["actual"] for v in total_cash_out_by_category.values())

    # Calculate opening balance
    opening_cash_in_query = (
        db.query(func.sum(CashIn.actual))
        .join(Development, CashIn.empreendimento_id == Development.id)
        .join(Filial, Development.filial_id == Filial.id)
        .filter(Filial.is_active == True, CashIn.ref_month < period_dates[0].strftime("%Y-%m"))
    )

    opening_cash_out_query = (
        db.query(func.sum(CashOut.realizado))
        .join(Filial, CashOut.filial_id == Filial.id)
        .filter(Filial.is_active == True, CashOut.mes_referencia < period_dates[0].strftime("%Y-%m"))
    )

    if not is_consolidated:
        opening_cash_in_query = opening_cash_in_query.filter(Development.filial_id == filial_id)
        opening_cash_out_query = opening_cash_out_query.filter(CashOut.filial_id == filial_id)

    if origem:
        opening_cash_in_query = opening_cash_in_query.filter(CashIn.origem == origem)
        opening_cash_out_query = opening_cash_out_query.filter(CashOut.origem == origem)

    opening_cash_in = opening_cash_in_query.scalar() or Decimal("0")
    opening_cash_out = opening_cash_out_query.scalar() or Decimal("0")

    balance_opening = Decimal(str(opening_cash_in)) - Decimal(str(opening_cash_out))
    balance_closing = balance_opening + total_cash_in_actual - total_cash_out_actual

    # Calculate variances
    cash_in_variance = total_cash_in_actual - total_cash_in_forecast
    cash_in_variance_pct = (
        (total_cash_in_actual / total_cash_in_forecast * 100) if total_cash_in_forecast > 0 else Decimal("0")
    )
    cash_out_variance = total_cash_out_actual - total_cash_out_budget
    cash_out_variance_pct = (
        (cash_out_variance / total_cash_out_budget * 100) if total_cash_out_budget > 0 else Decimal("0")
    )

    # Calculate immediate liquidity (balance_closing / avg_monthly_cash_out)
    num_months = len(period_dates)
    avg_monthly_cash_out = total_cash_out_actual / num_months if num_months > 0 else Decimal("0")
    immediate_liquidity_months = (
        (balance_closing / avg_monthly_cash_out) if avg_monthly_cash_out > 0 else Decimal("0")
    )

    # Calculate top cash in category
    top_cash_in_category = None
    top_cash_in_value = Decimal("0")
    category_labels = {
        "ativos": "Contratos Ativos",
        "recuperacoes": "Recuperações",
        "antecipacoes": "Antecipações",
        "outras": "Outras Entradas",
        "opex": "Custos Operacionais (OPEX)",
        "financeiras": "Despesas Financeiras",
        "capex": "Investimentos (CAPEX)",
        "tributos": "Tributos e Impostos",
        "outras_saidas": "Outras Saídas",
    }
    for category, values in total_cash_in_by_category.items():
        if values["actual"] > top_cash_in_value:
            top_cash_in_value = values["actual"]
            top_cash_in_category = TopCategory(
                name=category_labels.get(category, category.title()),
                value=float(values["actual"]),
            )

    # Calculate top cash out category
    top_cash_out_category = None
    top_cash_out_value = Decimal("0")
    for category, values in total_cash_out_by_category.items():
        if values["actual"] > top_cash_out_value:
            top_cash_out_value = values["actual"]
            top_cash_out_category = TopCategory(
                name=category_labels.get(category, category.title()),
                value=float(values["actual"]),
            )

    # Calculate portfolio stats (VP, LTV, prazo_medio, duration)
    portfolio_stats = None
    if is_consolidated:
        # Query PortfolioStats for all active developments
        portfolio_query = (
            db.query(PortfolioStats)
            .join(Development, PortfolioStats.empreendimento_id == Development.id)
            .join(Filial, Development.filial_id == Filial.id)
            .filter(
                Filial.is_active == True,
                PortfolioStats.ref_month <= period_dates[-1].strftime("%Y-%m"),
            )
        )
        if origem:
            portfolio_query = portfolio_query.filter(PortfolioStats.origem == origem)
        all_portfolios = (
            portfolio_query
            .order_by(PortfolioStats.empreendimento_id, PortfolioStats.ref_month.desc())
            .all()
        )

        # Keep only the most recent record for each development
        portfolio_by_dev = {}
        for record in all_portfolios:
            if record.empreendimento_id not in portfolio_by_dev:
                portfolio_by_dev[record.empreendimento_id] = record

        # Calculate weighted averages
        total_vp = Decimal("0")
        total_ltv_weighted = Decimal("0")
        total_prazo_weighted = Decimal("0")
        total_duration_weighted = Decimal("0")

        for portfolio_record in portfolio_by_dev.values():
            vp = Decimal(str(portfolio_record.vp))
            total_vp += vp
            total_ltv_weighted += Decimal(str(portfolio_record.ltv)) * vp
            total_prazo_weighted += Decimal(str(portfolio_record.prazo_medio)) * vp
            total_duration_weighted += Decimal(str(portfolio_record.duration)) * vp

        avg_ltv = (total_ltv_weighted / total_vp) if total_vp > 0 else Decimal("0")
        avg_prazo_medio = (total_prazo_weighted / total_vp) if total_vp > 0 else Decimal("0")
        avg_duration = (total_duration_weighted / total_vp) if total_vp > 0 else Decimal("0")

        portfolio_stats = CashFlowPortfolioStats(
            vp=float(total_vp),
            ltv=float(avg_ltv),
            prazo_medio=float(avg_prazo_medio),
            duration=float(avg_duration),
        )
    else:
        # Individual filial - get portfolio stats for developments in this filial
        portfolio_query = (
            db.query(PortfolioStats)
            .join(Development, PortfolioStats.empreendimento_id == Development.id)
            .filter(
                Development.filial_id == filial_id,
                PortfolioStats.ref_month <= period_dates[-1].strftime("%Y-%m"),
            )
        )
        if origem:
            portfolio_query = portfolio_query.filter(PortfolioStats.origem == origem)
        all_portfolios = (
            portfolio_query
            .order_by(PortfolioStats.empreendimento_id, PortfolioStats.ref_month.desc())
            .all()
        )

        portfolio_by_dev = {}
        for record in all_portfolios:
            if record.empreendimento_id not in portfolio_by_dev:
                portfolio_by_dev[record.empreendimento_id] = record

        total_vp = Decimal("0")
        total_ltv_weighted = Decimal("0")
        total_prazo_weighted = Decimal("0")
        total_duration_weighted = Decimal("0")

        for portfolio_record in portfolio_by_dev.values():
            vp = Decimal(str(portfolio_record.vp))
            total_vp += vp
            total_ltv_weighted += Decimal(str(portfolio_record.ltv)) * vp
            total_prazo_weighted += Decimal(str(portfolio_record.prazo_medio)) * vp
            total_duration_weighted += Decimal(str(portfolio_record.duration)) * vp

        avg_ltv = (total_ltv_weighted / total_vp) if total_vp > 0 else Decimal("0")
        avg_prazo_medio = (total_prazo_weighted / total_vp) if total_vp > 0 else Decimal("0")
        avg_duration = (total_duration_weighted / total_vp) if total_vp > 0 else Decimal("0")

        portfolio_stats = CashFlowPortfolioStats(
            vp=float(total_vp),
            ltv=float(avg_ltv),
            prazo_medio=float(avg_prazo_medio),
            duration=float(avg_duration),
        )

    return CashFlowResponse(
        filial_id=filial_id,
        filial_name=filial_name,
        is_consolidated=is_consolidated,
        start_date=start.isoformat(),
        end_date=end.isoformat(),
        total_cash_in=float(total_cash_in_actual),
        total_cash_in_forecast=float(total_cash_in_forecast),
        total_cash_out=float(total_cash_out_actual),
        total_cash_out_budget=float(total_cash_out_budget),
        balance_opening=float(balance_opening),
        balance_closing=float(balance_closing),
        cash_in_variance=float(cash_in_variance),
        cash_in_variance_pct=float(cash_in_variance_pct),
        cash_out_variance=float(cash_out_variance),
        cash_out_variance_pct=float(cash_out_variance_pct),
        cash_in_by_category=[
            CategoryBreakdown(category=cat, forecast=float(vals["forecast"]), actual=float(vals["actual"]))
            for cat, vals in total_cash_in_by_category.items()
        ],
        cash_out_by_category=[
            CategoryBreakdown(category=cat, budget=float(vals["budget"]), actual=float(vals["actual"]))
            for cat, vals in total_cash_out_by_category.items()
        ],
        immediate_liquidity_months=float(immediate_liquidity_months),
        top_cash_in_category=top_cash_in_category,
        top_cash_out_category=top_cash_out_category,
        portfolio_stats=portfolio_stats,
    )


@router.get("/portfolio-performance", response_model=PortfolioPerformanceResponse)
def get_portfolio_performance(
    start_date: str = Query(..., description="Data inicial (YYYY-MM-DD ou YYYY-MM)"),
    end_date: Optional[str] = Query(None, description="Data final (YYYY-MM-DD ou YYYY-MM)"),
    development_id: Optional[int] = Query(None, description="ID do empreendimento (omitir para consolidado)"),
    filial_id: Optional[int] = Query(None, description="ID da filial (omitir para consolidado)"),
    origem: Optional[str] = Query(None, description="Filtrar por origem: mega ou uau"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> PortfolioPerformanceResponse:
    """
    Retorna dados de performance do portfólio.

    - **start_date**: Data inicial do período
    - **end_date**: Data final do período (default: start_date)
    - **development_id**: Filtrar por empreendimento específico (omitir para consolidado)
    - **filial_id**: Filtrar por filial específica (omitir para consolidado)
    - **origem**: Filtrar por origem (mega = ABecker, uau = JVF)
    """
    from starke.domain.services.development_service import DevelopmentService

    origem = _validate_origem(origem)

    try:
        start = normalize_ref_date(_parse_date(start_date))
        end = normalize_ref_date(_parse_date(end_date)) if end_date else start
        period_dates = get_months_between(start, end)
        snapshot_date = period_dates[-1]
        month_strings = [d.strftime("%Y-%m") for d in period_dates]
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Formato de data inválido: {str(e)}")

    dev_service = DevelopmentService(db)
    all_developments = dev_service.get_all_developments(active_only=True, origem=origem)
    is_consolidated = development_id is None and filial_id is None
    filter_by_filial = filial_id is not None and development_id is None

    month_names_pt = ["Jan", "Fev", "Mar", "Abr", "Mai", "Jun", "Jul", "Ago", "Set", "Out", "Nov", "Dez"]
    temporal_yield_data = []
    delinquency_data = []

    if is_consolidated:
        # Batch queries for consolidated view
        portfolio_snapshot_query = (
            db.query(PortfolioStats)
            .join(Development, PortfolioStats.empreendimento_id == Development.id)
            .filter(Development.is_active == True, PortfolioStats.ref_month == snapshot_date.strftime("%Y-%m"))
        )
        if origem:
            portfolio_snapshot_query = portfolio_snapshot_query.filter(PortfolioStats.origem == origem)
        portfolio_snapshot_records = portfolio_snapshot_query.all()

        cash_in_query = (
            db.query(CashIn)
            .join(Development, CashIn.empreendimento_id == Development.id)
            .filter(Development.is_active == True, CashIn.ref_month.in_(month_strings))
        )
        if origem:
            cash_in_query = cash_in_query.filter(CashIn.origem == origem)
        all_cash_in = cash_in_query.all()

        cash_out_query = (
            db.query(CashOut)
            .join(Development, CashOut.filial_id == Development.id)
            .filter(Development.is_active == True, CashOut.mes_referencia.in_(month_strings))
        )
        if origem:
            cash_out_query = cash_out_query.filter(CashOut.origem == origem)
        all_cash_out = cash_out_query.all()

        portfolio_temporal_query = (
            db.query(PortfolioStats)
            .join(Development, PortfolioStats.empreendimento_id == Development.id)
            .filter(Development.is_active == True, PortfolioStats.ref_month.in_(month_strings))
        )
        if origem:
            portfolio_temporal_query = portfolio_temporal_query.filter(PortfolioStats.origem == origem)
        all_portfolio_temporal = portfolio_temporal_query.all()

        delinquency_query = (
            db.query(Delinquency)
            .join(Development, Delinquency.empreendimento_id == Development.id)
            .filter(Development.is_active == True, Delinquency.ref_month.in_(month_strings))
        )
        if origem:
            delinquency_query = delinquency_query.filter(Delinquency.origem == origem)
        all_delinquency = delinquency_query.all()

        # Process aggregated metrics
        total_vp = Decimal("0")
        total_contracts = 0
        total_active_contracts = 0
        weighted_ltv_sum = Decimal("0")
        weighted_prazo_sum = Decimal("0")
        weighted_duration_sum = Decimal("0")
        total_vp_for_weights = Decimal("0")
        total_monthly_receipts = Decimal("0")
        total_forecast = Decimal("0")
        total_actual = Decimal("0")

        for portfolio_record in portfolio_snapshot_records:
            vp = Decimal(str(portfolio_record.vp))
            total_vp += vp
            total_contracts += portfolio_record.total_contracts
            total_active_contracts += portfolio_record.active_contracts

            if vp > 0:
                weighted_ltv_sum += Decimal(str(portfolio_record.ltv)) * vp
                weighted_prazo_sum += Decimal(str(portfolio_record.prazo_medio)) * vp
                weighted_duration_sum += Decimal(str(portfolio_record.duration)) * vp
                total_vp_for_weights += vp

        for cash_in_record in all_cash_in:
            total_monthly_receipts += Decimal(str(cash_in_record.actual))
            total_forecast += Decimal(str(cash_in_record.forecast))
            total_actual += Decimal(str(cash_in_record.actual))

        avg_monthly_receipts = total_monthly_receipts / len(period_dates) if period_dates else Decimal("0")
        forecast_vs_actual_pct = (total_actual / total_forecast * 100) if total_forecast > 0 else Decimal("0")
        avg_ltv = (weighted_ltv_sum / total_vp_for_weights) if total_vp_for_weights > 0 else Decimal("0")
        avg_prazo_medio = (weighted_prazo_sum / total_vp_for_weights) if total_vp_for_weights > 0 else Decimal("0")
        avg_duration = (weighted_duration_sum / total_vp_for_weights) if total_vp_for_weights > 0 else Decimal("0")

        portfolio_stats = PortfolioStatsData(
            vp=float(total_vp),
            ltv=float(avg_ltv),
            prazo_medio=float(avg_prazo_medio),
            duration=float(avg_duration),
            total_contracts=total_contracts,
            active_contracts=total_active_contracts,
            total_receipts=float(total_monthly_receipts),
            avg_monthly_receipts=float(avg_monthly_receipts),
            forecast_vs_actual_pct=float(forecast_vs_actual_pct),
        )

        # Group data for temporal processing
        cash_in_by_dev_month = defaultdict(list)
        for r in all_cash_in:
            cash_in_by_dev_month[(r.empreendimento_id, r.ref_month)].append(r)

        cash_out_by_dev_month = defaultdict(list)
        for r in all_cash_out:
            cash_out_by_dev_month[(r.filial_id, r.mes_referencia)].append(r)

        portfolio_by_dev_month = {}
        for r in all_portfolio_temporal:
            portfolio_by_dev_month[(r.empreendimento_id, r.ref_month)] = r

        delinquency_by_dev_month = {}
        for r in all_delinquency:
            delinquency_by_dev_month[(r.empreendimento_id, r.ref_month)] = r

        # Generate temporal data
        for period_date in period_dates:
            month_str = period_date.strftime("%Y-%m")
            month_label = f"{month_names_pt[period_date.month - 1]} {period_date.year}"

            month_receipts_total = Decimal("0")
            month_deductions = Decimal("0")
            month_vp = Decimal("0")

            for dev in all_developments:
                cash_in_records = cash_in_by_dev_month.get((dev.id, month_str), [])
                month_receipts_total += sum(Decimal(str(r.actual)) for r in cash_in_records)

                cash_out_records = cash_out_by_dev_month.get((dev.id, month_str), [])
                month_deductions += sum(Decimal(str(r.realizado)) for r in cash_out_records)

                portfolio_month = portfolio_by_dev_month.get((dev.id, month_str))
                if portfolio_month:
                    month_vp += Decimal(str(portfolio_month.vp))

            month_net_receipts = month_receipts_total - month_deductions
            month_yield = (month_net_receipts / month_vp * 100) if month_vp > 0 else Decimal("0")

            temporal_yield_data.append(
                TemporalYieldData(
                    month=month_label,
                    receipts_total=float(month_receipts_total / 1000),
                    deductions=float(month_deductions / 1000),
                    net_receipts=float(month_net_receipts / 1000),
                    vp=float(month_vp / 1000),
                    yield_pct=float(month_yield),
                )
            )

            # Delinquency aggregation
            month_up_to_30 = Decimal("0")
            month_days_30_60 = Decimal("0")
            month_days_60_90 = Decimal("0")
            month_days_90_180 = Decimal("0")
            month_above_180 = Decimal("0")
            month_total = Decimal("0")
            qty_up_to_30 = qty_days_30_60 = qty_days_60_90 = qty_days_90_180 = qty_above_180 = qty_total = 0

            for dev in all_developments:
                delinquency_record = delinquency_by_dev_month.get((dev.id, month_str))
                if delinquency_record:
                    month_up_to_30 += Decimal(str(delinquency_record.up_to_30))
                    month_days_30_60 += Decimal(str(delinquency_record.days_30_60))
                    month_days_60_90 += Decimal(str(delinquency_record.days_60_90))
                    month_days_90_180 += Decimal(str(delinquency_record.days_90_180))
                    month_above_180 += Decimal(str(delinquency_record.above_180))
                    month_total += Decimal(str(delinquency_record.total))

                    details = delinquency_record.details or {}
                    quantities = details.get("quantities", {})
                    qty_up_to_30 += quantities.get("up_to_30", 0)
                    qty_days_30_60 += quantities.get("days_30_60", 0)
                    qty_days_60_90 += quantities.get("days_60_90", 0)
                    qty_days_90_180 += quantities.get("days_90_180", 0)
                    qty_above_180 += quantities.get("above_180", 0)
                    qty_total += quantities.get("total", 0)

            delinquency_data.append(
                DelinquencyData(
                    month=month_label,
                    up_to_30=float(month_up_to_30),
                    days_30_60=float(month_days_30_60),
                    days_60_90=float(month_days_60_90),
                    days_90_180=float(month_days_90_180),
                    above_180=float(month_above_180),
                    total=float(month_total),
                    qty_up_to_30=qty_up_to_30,
                    qty_days_30_60=qty_days_30_60,
                    qty_days_60_90=qty_days_60_90,
                    qty_days_90_180=qty_days_90_180,
                    qty_above_180=qty_above_180,
                    qty_total=qty_total,
                )
            )

    elif filter_by_filial:
        # Filter by filial - aggregate all developments of this filial
        filial = db.query(Filial).filter(Filial.id == filial_id, Filial.is_active == True).first()
        if not filial:
            raise HTTPException(status_code=404, detail="Filial não encontrada")

        # Get all developments for this filial
        filial_developments = [d for d in all_developments if d.filial_id == filial_id]
        filial_dev_ids = [d.id for d in filial_developments]

        # Batch queries filtered by filial
        portfolio_snapshot_query = (
            db.query(PortfolioStats)
            .filter(
                PortfolioStats.empreendimento_id.in_(filial_dev_ids),
                PortfolioStats.ref_month == snapshot_date.strftime("%Y-%m"),
            )
        )
        if origem:
            portfolio_snapshot_query = portfolio_snapshot_query.filter(PortfolioStats.origem == origem)
        portfolio_snapshot_records = portfolio_snapshot_query.all()

        cash_in_query = (
            db.query(CashIn)
            .filter(CashIn.empreendimento_id.in_(filial_dev_ids), CashIn.ref_month.in_(month_strings))
        )
        if origem:
            cash_in_query = cash_in_query.filter(CashIn.origem == origem)
        all_cash_in = cash_in_query.all()

        cash_out_query = (
            db.query(CashOut)
            .filter(CashOut.filial_id == filial_id, CashOut.mes_referencia.in_(month_strings))
        )
        if origem:
            cash_out_query = cash_out_query.filter(CashOut.origem == origem)
        all_cash_out = cash_out_query.all()

        portfolio_temporal_query = (
            db.query(PortfolioStats)
            .filter(PortfolioStats.empreendimento_id.in_(filial_dev_ids), PortfolioStats.ref_month.in_(month_strings))
        )
        if origem:
            portfolio_temporal_query = portfolio_temporal_query.filter(PortfolioStats.origem == origem)
        all_portfolio_temporal = portfolio_temporal_query.all()

        delinquency_query = (
            db.query(Delinquency)
            .filter(Delinquency.empreendimento_id.in_(filial_dev_ids), Delinquency.ref_month.in_(month_strings))
        )
        if origem:
            delinquency_query = delinquency_query.filter(Delinquency.origem == origem)
        all_delinquency = delinquency_query.all()

        # Process aggregated metrics (same logic as consolidated)
        total_vp = Decimal("0")
        total_contracts = 0
        total_active_contracts = 0
        weighted_ltv_sum = Decimal("0")
        weighted_prazo_sum = Decimal("0")
        weighted_duration_sum = Decimal("0")
        total_vp_for_weights = Decimal("0")
        total_monthly_receipts = Decimal("0")
        total_forecast = Decimal("0")
        total_actual = Decimal("0")

        for portfolio_record in portfolio_snapshot_records:
            vp = Decimal(str(portfolio_record.vp))
            total_vp += vp
            total_contracts += portfolio_record.total_contracts
            total_active_contracts += portfolio_record.active_contracts

            if vp > 0:
                weighted_ltv_sum += Decimal(str(portfolio_record.ltv)) * vp
                weighted_prazo_sum += Decimal(str(portfolio_record.prazo_medio)) * vp
                weighted_duration_sum += Decimal(str(portfolio_record.duration)) * vp
                total_vp_for_weights += vp

        for cash_in_record in all_cash_in:
            total_monthly_receipts += Decimal(str(cash_in_record.actual))
            total_forecast += Decimal(str(cash_in_record.forecast))
            total_actual += Decimal(str(cash_in_record.actual))

        avg_monthly_receipts = total_monthly_receipts / len(period_dates) if period_dates else Decimal("0")
        forecast_vs_actual_pct = (total_actual / total_forecast * 100) if total_forecast > 0 else Decimal("0")
        avg_ltv = (weighted_ltv_sum / total_vp_for_weights) if total_vp_for_weights > 0 else Decimal("0")
        avg_prazo_medio = (weighted_prazo_sum / total_vp_for_weights) if total_vp_for_weights > 0 else Decimal("0")
        avg_duration = (weighted_duration_sum / total_vp_for_weights) if total_vp_for_weights > 0 else Decimal("0")

        portfolio_stats = PortfolioStatsData(
            vp=float(total_vp),
            ltv=float(avg_ltv),
            prazo_medio=float(avg_prazo_medio),
            duration=float(avg_duration),
            total_contracts=total_contracts,
            active_contracts=total_active_contracts,
            total_receipts=float(total_monthly_receipts),
            avg_monthly_receipts=float(avg_monthly_receipts),
            forecast_vs_actual_pct=float(forecast_vs_actual_pct),
        )

        # Group data for temporal processing
        cash_in_by_dev_month = defaultdict(list)
        for r in all_cash_in:
            cash_in_by_dev_month[(r.empreendimento_id, r.ref_month)].append(r)

        cash_out_by_month = defaultdict(list)
        for r in all_cash_out:
            cash_out_by_month[r.mes_referencia].append(r)

        portfolio_by_dev_month = {}
        for r in all_portfolio_temporal:
            portfolio_by_dev_month[(r.empreendimento_id, r.ref_month)] = r

        delinquency_by_dev_month = {}
        for r in all_delinquency:
            delinquency_by_dev_month[(r.empreendimento_id, r.ref_month)] = r

        # Generate temporal data
        for period_date in period_dates:
            month_str = period_date.strftime("%Y-%m")
            month_label = f"{month_names_pt[period_date.month - 1]} {period_date.year}"

            month_receipts_total = Decimal("0")
            month_deductions = Decimal("0")
            month_vp = Decimal("0")

            for dev in filial_developments:
                cash_in_records = cash_in_by_dev_month.get((dev.id, month_str), [])
                month_receipts_total += sum(Decimal(str(r.actual)) for r in cash_in_records)

                portfolio_month = portfolio_by_dev_month.get((dev.id, month_str))
                if portfolio_month:
                    month_vp += Decimal(str(portfolio_month.vp))

            # CashOut is already filtered by filial
            cash_out_records = cash_out_by_month.get(month_str, [])
            month_deductions = sum(Decimal(str(r.realizado)) for r in cash_out_records)

            month_net_receipts = month_receipts_total - month_deductions
            month_yield = (month_net_receipts / month_vp * 100) if month_vp > 0 else Decimal("0")

            temporal_yield_data.append(
                TemporalYieldData(
                    month=month_label,
                    receipts_total=float(month_receipts_total / 1000),
                    deductions=float(month_deductions / 1000),
                    net_receipts=float(month_net_receipts / 1000),
                    vp=float(month_vp / 1000),
                    yield_pct=float(month_yield),
                )
            )

            # Delinquency aggregation for filial
            month_up_to_30 = Decimal("0")
            month_days_30_60 = Decimal("0")
            month_days_60_90 = Decimal("0")
            month_days_90_180 = Decimal("0")
            month_above_180 = Decimal("0")
            month_total = Decimal("0")
            qty_up_to_30 = qty_days_30_60 = qty_days_60_90 = qty_days_90_180 = qty_above_180 = qty_total = 0

            for dev in filial_developments:
                delinquency_record = delinquency_by_dev_month.get((dev.id, month_str))
                if delinquency_record:
                    month_up_to_30 += Decimal(str(delinquency_record.up_to_30))
                    month_days_30_60 += Decimal(str(delinquency_record.days_30_60))
                    month_days_60_90 += Decimal(str(delinquency_record.days_60_90))
                    month_days_90_180 += Decimal(str(delinquency_record.days_90_180))
                    month_above_180 += Decimal(str(delinquency_record.above_180))
                    month_total += Decimal(str(delinquency_record.total))

                    details = delinquency_record.details or {}
                    quantities = details.get("quantities", {})
                    qty_up_to_30 += quantities.get("up_to_30", 0)
                    qty_days_30_60 += quantities.get("days_30_60", 0)
                    qty_days_60_90 += quantities.get("days_60_90", 0)
                    qty_days_90_180 += quantities.get("days_90_180", 0)
                    qty_above_180 += quantities.get("above_180", 0)
                    qty_total += quantities.get("total", 0)

            delinquency_data.append(
                DelinquencyData(
                    month=month_label,
                    up_to_30=float(month_up_to_30),
                    days_30_60=float(month_days_30_60),
                    days_60_90=float(month_days_60_90),
                    days_90_180=float(month_days_90_180),
                    above_180=float(month_above_180),
                    total=float(month_total),
                    qty_up_to_30=qty_up_to_30,
                    qty_days_30_60=qty_days_30_60,
                    qty_days_60_90=qty_days_60_90,
                    qty_days_90_180=qty_days_90_180,
                    qty_above_180=qty_above_180,
                    qty_total=qty_total,
                )
            )

    else:
        # Individual development
        development = db.query(Development).filter(Development.id == development_id).first()
        if not development:
            raise HTTPException(status_code=404, detail="Empreendimento não encontrado")

        portfolio_query = (
            db.query(PortfolioStats)
            .filter(
                PortfolioStats.empreendimento_id == development_id,
                PortfolioStats.ref_month == snapshot_date.strftime("%Y-%m"),
            )
        )
        if origem:
            portfolio_query = portfolio_query.filter(PortfolioStats.origem == origem)
        portfolio_record = portfolio_query.first()

        total_monthly_receipts = Decimal("0")
        total_forecast = Decimal("0")
        total_actual = Decimal("0")

        for period_date in period_dates:
            month_str = period_date.strftime("%Y-%m")
            cash_in_query = (
                db.query(CashIn)
                .filter(CashIn.empreendimento_id == development_id, CashIn.ref_month == month_str)
            )
            if origem:
                cash_in_query = cash_in_query.filter(CashIn.origem == origem)
            cash_in_records = cash_in_query.all()
            total_monthly_receipts += sum(Decimal(str(r.actual)) for r in cash_in_records)
            total_forecast += sum(Decimal(str(r.forecast)) for r in cash_in_records)
            total_actual += sum(Decimal(str(r.actual)) for r in cash_in_records)

        avg_monthly_receipts = total_monthly_receipts / len(period_dates) if period_dates else Decimal("0")
        forecast_vs_actual_pct = (total_actual / total_forecast * 100) if total_forecast > 0 else Decimal("0")

        if portfolio_record:
            portfolio_stats = PortfolioStatsData(
                vp=float(portfolio_record.vp),
                ltv=float(portfolio_record.ltv),
                prazo_medio=float(portfolio_record.prazo_medio),
                duration=float(portfolio_record.duration),
                total_contracts=portfolio_record.total_contracts,
                active_contracts=portfolio_record.active_contracts,
                total_receipts=float(total_monthly_receipts),
                avg_monthly_receipts=float(avg_monthly_receipts),
                forecast_vs_actual_pct=float(forecast_vs_actual_pct),
            )
        else:
            portfolio_stats = PortfolioStatsData(
                vp=0,
                ltv=0,
                prazo_medio=0,
                duration=0,
                total_contracts=0,
                active_contracts=0,
                total_receipts=float(total_monthly_receipts),
                avg_monthly_receipts=float(avg_monthly_receipts),
                forecast_vs_actual_pct=float(forecast_vs_actual_pct),
            )

        # Generate temporal data for individual development
        for period_date in period_dates:
            month_str = period_date.strftime("%Y-%m")
            month_label = f"{month_names_pt[period_date.month - 1]} {period_date.year}"

            cash_in_query = (
                db.query(CashIn)
                .filter(CashIn.empreendimento_id == development_id, CashIn.ref_month == month_str)
            )
            if origem:
                cash_in_query = cash_in_query.filter(CashIn.origem == origem)
            cash_in_records = cash_in_query.all()
            month_receipts_total = sum(Decimal(str(r.actual)) for r in cash_in_records)

            cash_out_query = (
                db.query(CashOut)
                .filter(CashOut.filial_id == development_id, CashOut.mes_referencia == month_str)
            )
            if origem:
                cash_out_query = cash_out_query.filter(CashOut.origem == origem)
            cash_out_records = cash_out_query.all()
            month_deductions = sum(Decimal(str(r.realizado)) for r in cash_out_records)

            portfolio_month_query = (
                db.query(PortfolioStats)
                .filter(PortfolioStats.empreendimento_id == development_id, PortfolioStats.ref_month == month_str)
            )
            if origem:
                portfolio_month_query = portfolio_month_query.filter(PortfolioStats.origem == origem)
            portfolio_month = portfolio_month_query.first()
            month_vp = Decimal(str(portfolio_month.vp)) if portfolio_month else Decimal("0")

            month_net_receipts = month_receipts_total - month_deductions
            month_yield = (month_net_receipts / month_vp * 100) if month_vp > 0 else Decimal("0")

            temporal_yield_data.append(
                TemporalYieldData(
                    month=month_label,
                    receipts_total=float(month_receipts_total / 1000),
                    deductions=float(month_deductions / 1000),
                    net_receipts=float(month_net_receipts / 1000),
                    vp=float(month_vp / 1000),
                    yield_pct=float(month_yield),
                )
            )

            # Delinquency for individual development
            delinquency_query = (
                db.query(Delinquency)
                .filter(Delinquency.empreendimento_id == development_id, Delinquency.ref_month == month_str)
            )
            if origem:
                delinquency_query = delinquency_query.filter(Delinquency.origem == origem)
            delinquency_record = delinquency_query.first()

            if delinquency_record:
                details = delinquency_record.details or {}
                quantities = details.get("quantities", {})
                delinquency_data.append(
                    DelinquencyData(
                        month=month_label,
                        up_to_30=float(delinquency_record.up_to_30),
                        days_30_60=float(delinquency_record.days_30_60),
                        days_60_90=float(delinquency_record.days_60_90),
                        days_90_180=float(delinquency_record.days_90_180),
                        above_180=float(delinquency_record.above_180),
                        total=float(delinquency_record.total),
                        qty_up_to_30=quantities.get("up_to_30", 0),
                        qty_days_30_60=quantities.get("days_30_60", 0),
                        qty_days_60_90=quantities.get("days_60_90", 0),
                        qty_days_90_180=quantities.get("days_90_180", 0),
                        qty_above_180=quantities.get("above_180", 0),
                        qty_total=quantities.get("total", 0),
                    )
                )
            else:
                delinquency_data.append(
                    DelinquencyData(
                        month=month_label,
                        up_to_30=0,
                        days_30_60=0,
                        days_60_90=0,
                        days_90_180=0,
                        above_180=0,
                        total=0,
                    )
                )

    return PortfolioPerformanceResponse(
        portfolio_stats=portfolio_stats,
        temporal_yield_data=temporal_yield_data,
        delinquency_data=delinquency_data,
    )


@router.get("/evolution-data", response_model=EvolutionDataResponse)
def get_evolution_data(
    filial_id: Optional[int] = Query(None, description="ID da filial (omitir para consolidado)"),
    origem: Optional[str] = Query(None, description="Filtrar por origem: mega ou uau"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> EvolutionDataResponse:
    """
    Retorna dados de evolução do fluxo de caixa dos últimos 12 meses.

    - **filial_id**: Filtrar por filial específica (omitir para visão consolidada)
    - **origem**: Filtrar por origem (mega = ABecker, uau = JVF)
    """
    origem = _validate_origem(origem)
    # Calculate last 12 months period
    today = date.today()
    end_date = date(today.year, today.month, 1)
    start_date = end_date - timedelta(days=365)
    start_date = date(start_date.year, start_date.month, 1)

    period_dates = get_months_between(start_date, end_date)
    year_months = [f"{d.year:04d}-{d.month:02d}" for d in period_dates]

    is_consolidated = filial_id is None
    month_names_pt = ["Jan", "Fev", "Mar", "Abr", "Mai", "Jun", "Jul", "Ago", "Set", "Out", "Nov", "Dez"]

    if is_consolidated:
        cash_in_base = (
            db.query(CashIn.ref_month, func.sum(CashIn.actual).label("total_actual"))
            .join(Development, CashIn.empreendimento_id == Development.id)
            .join(Filial, Development.filial_id == Filial.id)
            .filter(Filial.is_active == True, CashIn.ref_month.in_(year_months))
        )
        if origem:
            cash_in_base = cash_in_base.filter(CashIn.origem == origem)
        cash_in_query = cash_in_base.group_by(CashIn.ref_month).all()

        cash_out_base = (
            db.query(CashOut.mes_referencia, func.sum(CashOut.realizado).label("total_actual"))
            .join(Filial, CashOut.filial_id == Filial.id)
            .filter(Filial.is_active == True, CashOut.mes_referencia.in_(year_months))
        )
        if origem:
            cash_out_base = cash_out_base.filter(CashOut.origem == origem)
        cash_out_query = cash_out_base.group_by(CashOut.mes_referencia).all()

        portfolio_base = (
            db.query(PortfolioStats.ref_month, func.sum(PortfolioStats.vp).label("total_vp"))
            .join(Development, PortfolioStats.empreendimento_id == Development.id)
            .join(Filial, Development.filial_id == Filial.id)
            .filter(Filial.is_active == True, PortfolioStats.ref_month.in_(year_months))
        )
        if origem:
            portfolio_base = portfolio_base.filter(PortfolioStats.origem == origem)
        portfolio_query = portfolio_base.group_by(PortfolioStats.ref_month).all()
    else:
        cash_in_base = (
            db.query(CashIn.ref_month, func.sum(CashIn.actual).label("total_actual"))
            .join(Development, CashIn.empreendimento_id == Development.id)
            .filter(Development.filial_id == filial_id, CashIn.ref_month.in_(year_months))
        )
        if origem:
            cash_in_base = cash_in_base.filter(CashIn.origem == origem)
        cash_in_query = cash_in_base.group_by(CashIn.ref_month).all()

        cash_out_base = (
            db.query(CashOut.mes_referencia, func.sum(CashOut.realizado).label("total_actual"))
            .filter(CashOut.filial_id == filial_id, CashOut.mes_referencia.in_(year_months))
        )
        if origem:
            cash_out_base = cash_out_base.filter(CashOut.origem == origem)
        cash_out_query = cash_out_base.group_by(CashOut.mes_referencia).all()

        portfolio_base = (
            db.query(PortfolioStats.ref_month, func.sum(PortfolioStats.vp).label("total_vp"))
            .join(Development, PortfolioStats.empreendimento_id == Development.id)
            .filter(Development.filial_id == filial_id, PortfolioStats.ref_month.in_(year_months))
        )
        if origem:
            portfolio_base = portfolio_base.filter(PortfolioStats.origem == origem)
        portfolio_query = portfolio_base.group_by(PortfolioStats.ref_month).all()

    # Build dictionaries
    cash_in_by_month = {row.ref_month: row.total_actual for row in cash_in_query}
    cash_out_by_month = {row.mes_referencia: row.total_actual for row in cash_out_query}
    portfolio_by_month = {row.ref_month: row.total_vp for row in portfolio_query}

    # Collect data
    temporal_data = []
    for year_month in year_months:
        year, month = year_month.split("-")
        month_label = f"{month_names_pt[int(month) - 1]}/{year}"

        month_cash_in = Decimal(str(cash_in_by_month.get(year_month, 0)))
        month_cash_out = Decimal(str(cash_out_by_month.get(year_month, 0)))
        month_vp = Decimal(str(portfolio_by_month.get(year_month, 0)))

        yield_mensal = (month_cash_in / month_vp) * 100 if month_vp > 0 else Decimal("0")

        temporal_data.append(
            EvolutionDataItem(
                month_year=month_label,
                cash_in=float(month_cash_in),
                cash_out=float(month_cash_out),
                net_flow=float(month_cash_in - month_cash_out),
                vp=float(month_vp),
                yield_mensal=float(yield_mensal),
            )
        )

    return EvolutionDataResponse(
        success=True,
        data=temporal_data,
        period={"start": str(start_date), "end": str(end_date), "months": len(temporal_data)},
    )
