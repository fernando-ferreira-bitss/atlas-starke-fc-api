"""Integration tests for report generation."""

from datetime import date
from decimal import Decimal

import pytest

from starke.domain.entities.cash_flow import (
    BalanceData,
    CashInCategory,
    CashInData,
    CashOutCategory,
    CashOutData,
    PortfolioStatsData,
)
from starke.presentation.report_builder import ReportBuilder


class TestReportGeneration:
    """Integration tests for report generation."""

    def test_build_complete_report(self):
        """Test building a complete HTML report."""
        builder = ReportBuilder()

        cash_in_list = [
            CashInData(
                empreendimento_id=1,
                empreendimento_nome="Test Empreendimento",
                ref_date=date(2024, 1, 31),
                category=CashInCategory.ATIVOS,
                forecast=Decimal("100000.00"),
                actual=Decimal("95000.00"),
            ),
            CashInData(
                empreendimento_id=1,
                empreendimento_nome="Test Empreendimento",
                ref_date=date(2024, 1, 31),
                category=CashInCategory.RECUPERACOES,
                forecast=Decimal("5000.00"),
                actual=Decimal("6000.00"),
            ),
        ]

        cash_out_list = [
            CashOutData(
                empreendimento_id=1,
                empreendimento_nome="Test Empreendimento",
                ref_date=date(2024, 1, 31),
                category=CashOutCategory.OPEX,
                budget=Decimal("30000.00"),
                actual=Decimal("28000.00"),
            ),
            CashOutData(
                empreendimento_id=1,
                empreendimento_nome="Test Empreendimento",
                ref_date=date(2024, 1, 31),
                category=CashOutCategory.FINANCEIRAS,
                budget=Decimal("10000.00"),
                actual=Decimal("10500.00"),
            ),
        ]

        balance = BalanceData(
            empreendimento_id=1,
            empreendimento_nome="Test Empreendimento",
            ref_date=date(2024, 1, 31),
            opening=Decimal("50000.00"),
            closing=Decimal("112500.00"),
            total_in=Decimal("101000.00"),
            total_out=Decimal("38500.00"),
        )

        portfolio_stats = PortfolioStatsData(
            empreendimento_id=1,
            empreendimento_nome="Test Empreendimento",
            ref_date=date(2024, 1, 31),
            vp=Decimal("5000000.00"),
            ltv=Decimal("75.5"),
            prazo_medio=Decimal("36.0"),
            duration=Decimal("28.5"),
            total_contracts=150,
            active_contracts=142,
        )

        html = builder.build_report(
            empreendimento_id=1,
            empreendimento_nome="Test Empreendimento",
            ref_date=date(2024, 1, 31),
            cash_in_list=cash_in_list,
            cash_out_list=cash_out_list,
            balance=balance,
            portfolio_stats=portfolio_stats,
        )

        # Verify HTML contains key elements
        assert "<!DOCTYPE html>" in html
        assert "Test Empreendimento" in html
        assert "31/01/2024" in html
        assert "Contratos Ativos" in html
        assert "Custos Operacionais" in html
        assert "R$ 5.000.000,00" in html  # VP formatted
        assert "142" in html  # Active contracts

    def test_build_report_without_portfolio_stats(self):
        """Test building report without portfolio stats."""
        builder = ReportBuilder()

        cash_in_list = [
            CashInData(
                empreendimento_id=1,
                empreendimento_nome="Test",
                ref_date=date(2024, 1, 31),
                category=CashInCategory.ATIVOS,
                forecast=Decimal("1000.00"),
                actual=Decimal("1000.00"),
            ),
        ]

        cash_out_list = [
            CashOutData(
                empreendimento_id=1,
                empreendimento_nome="Test",
                ref_date=date(2024, 1, 31),
                category=CashOutCategory.OPEX,
                budget=Decimal("500.00"),
                actual=Decimal("500.00"),
            ),
        ]

        balance = BalanceData(
            empreendimento_id=1,
            empreendimento_nome="Test",
            ref_date=date(2024, 1, 31),
            opening=Decimal("0"),
            closing=Decimal("500.00"),
            total_in=Decimal("1000.00"),
            total_out=Decimal("500.00"),
        )

        html = builder.build_report(
            empreendimento_id=1,
            empreendimento_nome="Test",
            ref_date=date(2024, 1, 31),
            cash_in_list=cash_in_list,
            cash_out_list=cash_out_list,
            balance=balance,
            portfolio_stats=None,
        )

        assert "<!DOCTYPE html>" in html
        assert "Test" in html
