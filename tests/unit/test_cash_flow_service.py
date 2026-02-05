"""Unit tests for CashFlowService."""

from datetime import date
from decimal import Decimal

import pytest

from starke.domain.entities.cash_flow import CashInCategory, CashOutCategory
from starke.domain.services.cash_flow_service import CashFlowService


class TestCashFlowService:
    """Tests for CashFlowService."""

    def test_calculate_cash_in_from_parcelas(self, db_session):
        """Test cash in calculation from installments."""
        service = CashFlowService(db_session)

        parcelas = [
            {
                "dataVencimento": "2024-01-15",
                "valorParcela": 1000.00,
                "valorPago": 1000.00,
                "status": "pago",
                "tipo": "normal",
            },
            {
                "dataVencimento": "2024-01-20",
                "valorParcela": 2000.00,
                "valorPago": 2000.00,
                "status": "pago",
                "tipo": "antecipacao",
            },
        ]

        cash_in_list = service.calculate_cash_in_from_parcelas(
            parcelas=parcelas,
            empreendimento_id=1,
            empreendimento_nome="Test",
            ref_date=date(2024, 1, 31),
        )

        assert len(cash_in_list) == 4  # All categories
        ativos = next(c for c in cash_in_list if c.category == CashInCategory.ATIVOS)
        antecipacoes = next(
            c for c in cash_in_list if c.category == CashInCategory.ANTECIPACOES
        )

        assert ativos.actual == Decimal("1000.00")
        assert antecipacoes.actual == Decimal("2000.00")

    def test_calculate_portfolio_stats(self, db_session):
        """Test portfolio statistics calculation."""
        service = CashFlowService(db_session)

        contratos = [
            {
                "codigoContrato": 1,
                "status": "ativo",
                "valorContrato": 100000.00,
                "saldoDevedor": 80000.00,
            },
            {
                "codigoContrato": 2,
                "status": "ativo",
                "valorContrato": 150000.00,
                "saldoDevedor": 120000.00,
            },
        ]

        stats = service.calculate_portfolio_stats(
            contratos=contratos,
            empreendimento_id=1,
            empreendimento_nome="Test",
            ref_date=date(2024, 1, 31),
        )

        assert stats.total_contracts == 2
        assert stats.active_contracts == 2
        assert stats.vp == Decimal("250000.00")
        assert stats.total_receivable == Decimal("200000.00")

    def test_calculate_balance(self, db_session):
        """Test balance calculation."""
        service = CashFlowService(db_session)

        # Create mock cash in/out lists
        from starke.domain.entities.cash_flow import CashInData, CashOutData

        cash_in_list = [
            CashInData(
                empreendimento_id=1,
                empreendimento_nome="Test",
                ref_date=date(2024, 1, 31),
                category=CashInCategory.ATIVOS,
                forecast=Decimal("1000.00"),
                actual=Decimal("1000.00"),
            )
        ]

        cash_out_list = [
            CashOutData(
                empreendimento_id=1,
                empreendimento_nome="Test",
                ref_date=date(2024, 1, 31),
                category=CashOutCategory.OPEX,
                budget=Decimal("500.00"),
                actual=Decimal("450.00"),
            )
        ]

        balance = service.calculate_balance(
            cash_in_list=cash_in_list,
            cash_out_list=cash_out_list,
            empreendimento_id=1,
            empreendimento_nome="Test",
            ref_date=date(2024, 1, 31),
            opening_balance=Decimal("5000.00"),
        )

        assert balance.opening == Decimal("5000.00")
        assert balance.total_in == Decimal("1000.00")
        assert balance.total_out == Decimal("450.00")
        assert balance.closing == Decimal("5550.00")
        assert balance.net_flow == Decimal("550.00")
