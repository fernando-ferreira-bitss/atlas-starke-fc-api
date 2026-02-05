"""Unit tests for domain entities."""

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
from starke.domain.entities.contracts import ContratoData, ParcelaData


class TestCashInData:
    """Tests for CashInData entity."""

    def test_create_cash_in_data(self):
        """Test creating a CashInData instance."""
        cash_in = CashInData(
            empreendimento_id=1,
            empreendimento_nome="Test",
            ref_date=date(2024, 1, 1),
            category=CashInCategory.ATIVOS,
            forecast=Decimal("1000.00"),
            actual=Decimal("950.00"),
        )

        assert cash_in.empreendimento_id == 1
        assert cash_in.category == CashInCategory.ATIVOS
        assert cash_in.forecast == Decimal("1000.00")
        assert cash_in.actual == Decimal("950.00")

    def test_variance_calculation(self):
        """Test variance calculation."""
        cash_in = CashInData(
            empreendimento_id=1,
            empreendimento_nome="Test",
            ref_date=date(2024, 1, 1),
            category=CashInCategory.ATIVOS,
            forecast=Decimal("1000.00"),
            actual=Decimal("950.00"),
        )

        assert cash_in.variance == Decimal("-50.00")
        assert cash_in.variance_pct == Decimal("-5.0")

    def test_positive_variance(self):
        """Test positive variance calculation."""
        cash_in = CashInData(
            empreendimento_id=1,
            empreendimento_nome="Test",
            ref_date=date(2024, 1, 1),
            category=CashInCategory.ATIVOS,
            forecast=Decimal("1000.00"),
            actual=Decimal("1100.00"),
        )

        assert cash_in.variance == Decimal("100.00")
        assert cash_in.variance_pct == Decimal("10.0")


class TestCashOutData:
    """Tests for CashOutData entity."""

    def test_create_cash_out_data(self):
        """Test creating a CashOutData instance."""
        cash_out = CashOutData(
            empreendimento_id=1,
            empreendimento_nome="Test",
            ref_date=date(2024, 1, 1),
            category=CashOutCategory.OPEX,
            budget=Decimal("500.00"),
            actual=Decimal("550.00"),
        )

        assert cash_out.empreendimento_id == 1
        assert cash_out.category == CashOutCategory.OPEX
        assert cash_out.budget == Decimal("500.00")
        assert cash_out.actual == Decimal("550.00")

    def test_variance_calculation(self):
        """Test variance calculation."""
        cash_out = CashOutData(
            empreendimento_id=1,
            empreendimento_nome="Test",
            ref_date=date(2024, 1, 1),
            category=CashOutCategory.OPEX,
            budget=Decimal("500.00"),
            actual=Decimal("550.00"),
        )

        assert cash_out.variance == Decimal("50.00")
        assert cash_out.variance_pct == Decimal("10.0")


class TestBalanceData:
    """Tests for BalanceData entity."""

    def test_create_balance_data(self):
        """Test creating a BalanceData instance."""
        balance = BalanceData(
            empreendimento_id=1,
            empreendimento_nome="Test",
            ref_date=date(2024, 1, 1),
            opening=Decimal("5000.00"),
            closing=Decimal("5450.00"),
            total_in=Decimal("1000.00"),
            total_out=Decimal("550.00"),
        )

        assert balance.opening == Decimal("5000.00")
        assert balance.closing == Decimal("5450.00")

    def test_net_flow_calculation(self):
        """Test net flow calculation."""
        balance = BalanceData(
            empreendimento_id=1,
            empreendimento_nome="Test",
            ref_date=date(2024, 1, 1),
            opening=Decimal("5000.00"),
            closing=Decimal("5450.00"),
            total_in=Decimal("1000.00"),
            total_out=Decimal("550.00"),
        )

        assert balance.net_flow == Decimal("450.00")

    def test_variance_calculation(self):
        """Test balance variance calculation."""
        balance = BalanceData(
            empreendimento_id=1,
            empreendimento_nome="Test",
            ref_date=date(2024, 1, 1),
            opening=Decimal("5000.00"),
            closing=Decimal("5450.00"),
            total_in=Decimal("1000.00"),
            total_out=Decimal("550.00"),
        )

        assert balance.variance == Decimal("450.00")
        assert balance.variance_pct == Decimal("9.0")


class TestParcelaData:
    """Tests for ParcelaData entity."""

    def test_create_parcela_data(self):
        """Test creating a ParcelaData instance."""
        parcela = ParcelaData(
            codigo_parcela=1,
            codigo_contrato=100,
            numero_parcela=1,
            data_vencimento=date(2024, 1, 1),
            valor_parcela=Decimal("1000.00"),
            status="pago",
        )

        assert parcela.codigo_parcela == 1
        assert parcela.valor_parcela == Decimal("1000.00")
        assert parcela.status == "pago"

    def test_is_paid(self):
        """Test is_paid property."""
        parcela_paid = ParcelaData(
            codigo_parcela=1,
            codigo_contrato=100,
            numero_parcela=1,
            data_vencimento=date(2024, 1, 1),
            valor_parcela=Decimal("1000.00"),
            status="pago",
        )

        parcela_open = ParcelaData(
            codigo_parcela=2,
            codigo_contrato=100,
            numero_parcela=2,
            data_vencimento=date(2024, 2, 1),
            valor_parcela=Decimal("1000.00"),
            status="aberto",
        )

        assert parcela_paid.is_paid is True
        assert parcela_open.is_paid is False

    def test_valor_total_calculation(self):
        """Test valor_total calculation."""
        parcela = ParcelaData(
            codigo_parcela=1,
            codigo_contrato=100,
            numero_parcela=1,
            data_vencimento=date(2024, 1, 1),
            valor_parcela=Decimal("1000.00"),
            juros=Decimal("50.00"),
            multa=Decimal("20.00"),
            desconto=Decimal("10.00"),
            status="aberto",
        )

        assert parcela.valor_total == Decimal("1060.00")


class TestPortfolioStatsData:
    """Tests for PortfolioStatsData entity."""

    def test_create_portfolio_stats(self):
        """Test creating a PortfolioStatsData instance."""
        stats = PortfolioStatsData(
            empreendimento_id=1,
            empreendimento_nome="Test",
            ref_date=date(2024, 1, 1),
            vp=Decimal("1000000.00"),
            ltv=Decimal("80.00"),
            prazo_medio=Decimal("36.5"),
            duration=Decimal("24.3"),
            total_contracts=100,
            active_contracts=85,
        )

        assert stats.vp == Decimal("1000000.00")
        assert stats.total_contracts == 100
        assert stats.active_contracts == 85

    def test_active_ratio_calculation(self):
        """Test active ratio calculation."""
        stats = PortfolioStatsData(
            empreendimento_id=1,
            empreendimento_nome="Test",
            ref_date=date(2024, 1, 1),
            vp=Decimal("1000000.00"),
            ltv=Decimal("80.00"),
            prazo_medio=Decimal("36.5"),
            duration=Decimal("24.3"),
            total_contracts=100,
            active_contracts=85,
        )

        assert stats.active_ratio == Decimal("85.0")

    def test_active_ratio_with_zero_contracts(self):
        """Test active ratio with zero contracts."""
        stats = PortfolioStatsData(
            empreendimento_id=1,
            empreendimento_nome="Test",
            ref_date=date(2024, 1, 1),
            vp=Decimal("0"),
            ltv=Decimal("0"),
            prazo_medio=Decimal("0"),
            duration=Decimal("0"),
            total_contracts=0,
            active_contracts=0,
        )

        assert stats.active_ratio == Decimal("0")


class TestContratoData:
    """Tests for ContratoData entity."""

    def test_normalize_cpf_cnpj(self):
        """Test CPF/CNPJ normalization."""
        contrato = ContratoData(
            codigo_contrato=1,
            codigo_empreendimento=1,
            cpf_cnpj="123.456.789-01",
            valor_contrato=Decimal("100000.00"),
        )

        assert contrato.cpf_cnpj == "12345678901"
