"""HTML report builder using Jinja2 templates."""

from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any, Optional, Union

from jinja2 import Environment, FileSystemLoader, select_autoescape

from starke.core.logging import get_logger
from starke.domain.entities.cash_flow import (
    BalanceData,
    CashInCategory,
    CashInData,
    CashOutCategory,
    CashOutData,
    PortfolioStatsData,
)

logger = get_logger(__name__)


class ReportBuilder:
    """Builder for generating HTML cash flow reports."""

    # Category labels for display
    CASH_IN_LABELS = {
        CashInCategory.ATIVOS: "Contratos Ativos",
        CashInCategory.RECUPERACOES: "Recuperações",
        CashInCategory.ANTECIPACOES: "Antecipações",
        CashInCategory.OUTRAS: "Outras Entradas",
    }

    CASH_OUT_LABELS = {
        CashOutCategory.OPEX: "Custos Operacionais (OPEX)",
        CashOutCategory.FINANCEIRAS: "Despesas Financeiras",
        CashOutCategory.CAPEX: "Investimentos (CAPEX)",
        CashOutCategory.DISTRIBUICOES: "Distribuições",
    }

    def __init__(self) -> None:
        """Initialize report builder with Jinja2 environment."""
        templates_dir = Path(__file__).parent / "templates"
        self.env = Environment(
            loader=FileSystemLoader(str(templates_dir)),
            autoescape=select_autoescape(["html", "xml"]),
            trim_blocks=True,
            lstrip_blocks=True,
        )

        # Add custom filters
        self.env.filters["currency"] = self._format_currency
        self.env.filters["percentage"] = self._format_percentage

        logger.info("Report builder initialized", templates_dir=str(templates_dir))

    @staticmethod
    def _format_currency(value: Union[float, Decimal]) -> str:
        """Format value as Brazilian currency."""
        return f"R$ {float(value):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

    @staticmethod
    def _format_percentage(value: Union[float, Decimal]) -> str:
        """Format value as percentage."""
        return f"{float(value):.1f}%"

    def build_report(
        self,
        empreendimento_id: Optional[int],
        empreendimento_nome: str,
        ref_date: date,
        cash_in_list: list[CashInData],
        cash_out_list: list[CashOutData],
        balance: BalanceData,
        portfolio_stats: Optional[PortfolioStatsData] = None,
        for_email: bool = False,
    ) -> str:
        """
        Build HTML report for an empreendimento.

        Args:
            empreendimento_id: Empreendimento ID (None for consolidated)
            empreendimento_nome: Empreendimento name
            ref_date: Reference date
            cash_in_list: List of cash inflows
            cash_out_list: List of cash outflows
            balance: Balance data
            portfolio_stats: Portfolio statistics (optional)
            for_email: If True, use email-compatible template without Chart.js

        Returns:
            HTML report string
        """
        logger.info(
            "Building report",
            empreendimento_id=empreendimento_id,
            empreendimento_nome=empreendimento_nome,
            ref_date=ref_date.isoformat(),
        )

        # Prepare cash in data
        cash_in_data = []
        total_forecast = Decimal("0")
        total_actual = Decimal("0")

        for cash_in in cash_in_list:
            cash_in_data.append({
                "category": cash_in.category.value,
                "category_label": self.CASH_IN_LABELS.get(
                    cash_in.category, cash_in.category.value
                ),
                "forecast": float(cash_in.forecast),
                "actual": float(cash_in.actual),
                "variance": float(cash_in.variance),
                "variance_pct": float(cash_in.variance_pct),
            })
            total_forecast += cash_in.forecast
            total_actual += cash_in.actual

        # Calculate cash in variance
        cash_in_variance_pct = (
            ((total_actual - total_forecast) / total_forecast * 100)
            if total_forecast != 0
            else Decimal("0")
        )

        # Prepare cash out data
        cash_out_data = []
        total_budget = Decimal("0")
        total_out_actual = Decimal("0")

        for cash_out in cash_out_list:
            cash_out_data.append({
                "category": cash_out.category.value,
                "category_label": self.CASH_OUT_LABELS.get(
                    cash_out.category, cash_out.category.value
                ),
                "budget": float(cash_out.budget),
                "actual": float(cash_out.actual),
                "variance": float(cash_out.variance),
                "variance_pct": float(cash_out.variance_pct),
            })
            total_budget += cash_out.budget
            total_out_actual += cash_out.actual

        # Calculate cash out variance
        cash_out_variance_pct = (
            ((total_out_actual - total_budget) / total_budget * 100)
            if total_budget != 0
            else Decimal("0")
        )

        # Prepare balance data
        balance_variance_pct = float(balance.variance_pct)
        net_flow = float(balance.net_flow)

        # Prepare context
        context = {
            "empreendimento_id": empreendimento_id,
            "empreendimento_nome": empreendimento_nome,
            "report_date": ref_date.strftime("%d/%m/%Y"),
            "generation_time": datetime.now().strftime("%d/%m/%Y às %H:%M"),
            # Cash in
            "cash_in_data": cash_in_data,
            "total_cash_in_forecast": float(total_forecast),
            "total_cash_in": float(total_actual),
            "cash_in_variance_pct": float(cash_in_variance_pct),
            # Cash out
            "cash_out_data": cash_out_data,
            "total_cash_out_budget": float(total_budget),
            "total_cash_out": float(total_out_actual),
            "cash_out_variance_pct": float(cash_out_variance_pct),
            # Balance
            "balance_opening": float(balance.opening),
            "balance_closing": float(balance.closing),
            "balance_variance_pct": balance_variance_pct,
            "net_flow": net_flow,
            # Portfolio stats
            "portfolio_stats": self._prepare_portfolio_stats(portfolio_stats) if portfolio_stats else None,
        }

        # Render template (use email template if for_email=True)
        template_name = "report_email.html" if for_email else "report.html"
        template = self.env.get_template(template_name)
        html = template.render(**context)

        logger.info(
            "Report built successfully",
            empreendimento_id=empreendimento_id,
            html_length=len(html),
        )

        return html

    def _prepare_portfolio_stats(self, stats: PortfolioStatsData) -> dict[str, Any]:
        """Prepare portfolio stats for template."""
        return {
            "vp": float(stats.vp),
            "ltv": float(stats.ltv),
            "prazo_medio": float(stats.prazo_medio),
            "duration": float(stats.duration),
            "total_contracts": stats.total_contracts,
            "active_contracts": stats.active_contracts,
            "active_ratio": float(stats.active_ratio),
        }

    def build_consolidated_report(
        self,
        ref_date: date,
        empreendimento_reports: list[dict[str, Any]],
    ) -> str:
        """
        Build consolidated report for all empreendimentos.

        Args:
            ref_date: Reference date
            empreendimento_reports: List of individual report data

        Returns:
            HTML consolidated report
        """
        logger.info(
            "Building consolidated report",
            ref_date=ref_date.isoformat(),
            empreendimento_count=len(empreendimento_reports),
        )

        # Aggregate all data
        total_cash_in = Decimal("0")
        total_cash_out = Decimal("0")
        total_opening = Decimal("0")
        total_closing = Decimal("0")

        for report in empreendimento_reports:
            total_cash_in += Decimal(str(report.get("total_cash_in", 0)))
            total_cash_out += Decimal(str(report.get("total_cash_out", 0)))
            total_opening += Decimal(str(report.get("balance_opening", 0)))
            total_closing += Decimal(str(report.get("balance_closing", 0)))

        net_flow = total_cash_in - total_cash_out
        balance_variance_pct = (
            ((total_closing - total_opening) / total_opening * 100)
            if total_opening != 0
            else Decimal("0")
        )

        context = {
            "empreendimento_nome": "CONSOLIDADO",
            "report_date": ref_date.strftime("%d/%m/%Y"),
            "generation_time": datetime.now().strftime("%d/%m/%Y às %H:%M"),
            "total_cash_in": float(total_cash_in),
            "total_cash_out": float(total_cash_out),
            "balance_opening": float(total_opening),
            "balance_closing": float(total_closing),
            "net_flow": float(net_flow),
            "balance_variance_pct": float(balance_variance_pct),
            "empreendimento_reports": empreendimento_reports,
            "empreendimento_count": len(empreendimento_reports),
        }

        # TODO: Create consolidated template
        # For now, use the regular template with consolidated data
        template = self.env.get_template("report.html")
        html = template.render(**context)

        logger.info("Consolidated report built successfully")
        return html
