"""Advanced portfolio metrics calculator - Duration, LTV, and other financial metrics."""

import logging
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple

from starke.core.config_loader import get_mega_config

logger = logging.getLogger(__name__)


class PortfolioCalculator:
    """Calculate advanced portfolio metrics from contract and installment data."""

    def __init__(self):
        """Initialize calculator with configuration."""
        self.config = get_mega_config()

    # ============================================
    # Duration (Macaulay Duration)
    # ============================================

    def calculate_duration(
        self,
        parcelas: List[Dict[str, Any]],
        taxa_desconto: Optional[float] = None,
        ref_date: Optional[date] = None,
    ) -> float:
        """
        Calculate Macaulay Duration of portfolio installments.

        Duration measures the weighted average time until cash flows are received,
        taking into account the time value of money.

        Formula:
            Duration = Σ(t × PV(CF_t)) / Σ(PV(CF_t))

        Where:
            t = time period (in years) until cash flow
            CF_t = cash flow at time t
            PV(CF_t) = present value of cash flow at time t

        Args:
            parcelas: List of installment dicts from Mega API
            taxa_desconto: Discount rate (annual). If None, uses config default
            ref_date: Reference date (defaults to today)

        Returns:
            Duration in years
        """
        if ref_date is None:
            ref_date = date.today()

        if taxa_desconto is None:
            taxa_desconto = self.config.get_taxa_desconto()

        numerador = Decimal("0")  # Σ(t × PV(CF_t))
        denominador = Decimal("0")  # Σ(PV(CF_t))

        for parcela in parcelas:
            # Only consider installments with outstanding balance
            # Saldo = vlr_corrigido - vlr_pago
            vlr_corrigido = self._parse_decimal(parcela.get("vlr_corrigido", 0))
            vlr_pago = self._parse_decimal(parcela.get("vlr_pago", 0))
            saldo = vlr_corrigido - vlr_pago

            if saldo <= 0:
                continue

            # Get due date
            dt_vencimento = self._parse_date(parcela.get("data_vencimento"))
            if not dt_vencimento:
                logger.warning(f"Parcela {parcela.get('sequencia')} missing due date, skipping")
                continue

            # Calculate time until payment (in years)
            dias_ate_vencimento = (dt_vencimento - ref_date).days

            # Skip if already paid or too overdue
            if dias_ate_vencimento < self.config.get_prazo_minimo_vp_dias():
                continue

            anos_ate_vencimento = Decimal(dias_ate_vencimento) / Decimal(365)

            # Calculate present value of cash flow
            # PV = CF / (1 + r)^t
            try:
                discount_factor = pow((1 + float(taxa_desconto)), float(anos_ate_vencimento))
                pv_fluxo = saldo / Decimal(str(discount_factor))
            except (OverflowError, ValueError) as e:
                logger.warning(f"Error calculating PV for parcela {parcela.get('sequencia')}: {e}")
                continue

            # Add to weighted sum
            numerador += anos_ate_vencimento * pv_fluxo
            denominador += pv_fluxo

        # Calculate duration
        if denominador > 0:
            duration = float(numerador / denominador)
            return round(duration, 2)

        return 0.0

    # ============================================
    # LTV (Loan-to-Value)
    # ============================================

    def calculate_ltv(
        self,
        vp: float,
        contratos: List[Dict[str, Any]],
        unidades_data: Optional[List[Dict[str, Any]]] = None,
    ) -> float:
        """
        Calculate LTV (Loan-to-Value) ratio.

        LTV = VP / Total Value of Units Sold (IPCA-adjusted)

        Args:
            vp: Valor Presente (outstanding receivables)
            contratos: List of contract dicts from Mega API
            unidades_data: Optional list of unit data with values

        Returns:
            LTV as percentage (e.g., 65.5 for 65.5%)
        """
        # Calculate total value of contracts (represents value of units sold)
        # Use valor_atualizado_ipca if available, otherwise fall back to valor_contrato
        total_valor_contratos = Decimal("0")

        for contrato in contratos:
            # Only consider active contracts
            status = contrato.get("status_contrato")
            if not self.config.is_contrato_ativo(status):
                continue

            # Prefer IPCA-adjusted value if available
            valor_atualizado = contrato.get("valor_atualizado_ipca")
            if valor_atualizado:
                valor = self._parse_decimal(valor_atualizado)
            else:
                # Fall back to original contract value
                valor = self._parse_decimal(contrato.get("valor_contrato", 0))

            total_valor_contratos += valor

        if total_valor_contratos == 0:
            return 0.0

        # Calculate LTV
        ltv = (Decimal(str(vp)) / total_valor_contratos) * 100

        return float(round(ltv, 2))

    def calculate_ltv_from_units(
        self, vp: float, unidades: List[Dict[str, Any]], contratos: List[Dict[str, Any]]
    ) -> float:
        """
        Calculate LTV using unit values (more accurate).

        This method requires unit data with actual sale values.

        Args:
            vp: Valor Presente (outstanding receivables)
            unidades: List of unit dicts from Mega API
            contratos: List of contract dicts to link units to sales

        Returns:
            LTV as percentage
        """
        # Create mapping of unit ID to contract value
        unit_to_contract = {}
        for contrato in contratos:
            if not self.config.is_contrato_ativo(contrato.get("status_contrato")):
                continue

            # Get unit information from contract
            unidade_id = contrato.get("und_in_codigo")
            valor = self._parse_decimal(contrato.get("valor_contrato", 0))

            if unidade_id and valor > 0:
                unit_to_contract[unidade_id] = valor

        # Calculate total value of sold units
        total_valor_vendas = sum(unit_to_contract.values())

        if total_valor_vendas == 0:
            return 0.0

        # Calculate LTV
        ltv = (Decimal(str(vp)) / Decimal(str(total_valor_vendas))) * 100

        return float(round(ltv, 2))

    # ============================================
    # Portfolio Statistics
    # ============================================

    def calculate_portfolio_stats(
        self,
        contratos: List[Dict[str, Any]],
        parcelas: List[Dict[str, Any]],
        ref_date: Optional[date] = None,
        taxa_desconto: Optional[float] = None,
        unidades_data: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """
        Calculate complete portfolio statistics.

        Args:
            contratos: List of contract dicts
            parcelas: List of installment dicts
            ref_date: Reference date (defaults to today)
            taxa_desconto: Discount rate for duration calculation
            unidades_data: Optional unit data for LTV calculation

        Returns:
            Dict with all portfolio metrics
        """
        if ref_date is None:
            ref_date = date.today()

        # 1. Count contracts
        total_contracts = len(contratos)
        active_contracts = sum(1 for c in contratos if self.config.is_contrato_ativo(c.get("status_contrato")))

        # 2. Calculate VP (Valor Presente)
        vp = self._calculate_vp(parcelas, ref_date)

        # 3. Calculate Prazo Médio (weighted average term)
        prazo_medio = self._calculate_prazo_medio(contratos, parcelas)

        # 4. Calculate Duration
        duration = self.calculate_duration(parcelas, taxa_desconto, ref_date)

        # 5. Calculate LTV
        if unidades_data:
            ltv = self.calculate_ltv_from_units(vp, unidades_data, contratos)
        else:
            ltv = self.calculate_ltv(vp, contratos)

        return {
            "vp": round(vp, 2),
            "ltv": ltv,
            "prazo_medio": prazo_medio,
            "duration": duration,
            "total_contracts": total_contracts,
            "active_contracts": active_contracts,
        }

    # ============================================
    # Delinquency Analysis
    # ============================================

    def calculate_delinquency_rate(
        self, delinquency_total: float, vp: float
    ) -> float:
        """
        Calculate delinquency rate as percentage of VP.

        Args:
            delinquency_total: Total delinquent amount
            vp: Valor Presente (total receivables)

        Returns:
            Delinquency rate as percentage
        """
        if vp == 0:
            return 0.0

        rate = (Decimal(str(delinquency_total)) / Decimal(str(vp))) * 100

        return float(round(rate, 2))

    def calculate_coverage_ratio(
        self, provisions: float, delinquency_total: float
    ) -> float:
        """
        Calculate provision coverage ratio.

        Coverage Ratio = Provisions / Total Delinquent Amount

        Args:
            provisions: Total provisions for bad debt
            delinquency_total: Total delinquent amount

        Returns:
            Coverage ratio as percentage
        """
        if delinquency_total == 0:
            return 0.0

        ratio = (Decimal(str(provisions)) / Decimal(str(delinquency_total))) * 100

        return float(round(ratio, 2))

    # ============================================
    # Cash Flow Metrics
    # ============================================

    def calculate_cash_flow_variance(
        self, forecast: float, actual: float
    ) -> Tuple[float, float]:
        """
        Calculate variance between forecast and actual.

        Args:
            forecast: Forecasted amount
            actual: Actual amount

        Returns:
            Tuple of (variance_amount, variance_percentage)
        """
        variance_amount = Decimal(str(actual)) - Decimal(str(forecast))

        if forecast == 0:
            variance_pct = 0.0
        else:
            variance_pct = (variance_amount / Decimal(str(forecast))) * 100

        return (
            float(round(variance_amount, 2)),
            float(round(variance_pct, 2)),
        )

    def calculate_burn_rate(
        self, cash_out_monthly: List[float], periods: int = 3
    ) -> float:
        """
        Calculate average monthly burn rate (cash out).

        Args:
            cash_out_monthly: List of monthly cash out values
            periods: Number of recent periods to average (default: 3 months)

        Returns:
            Average monthly burn rate
        """
        if not cash_out_monthly:
            return 0.0

        recent = cash_out_monthly[-periods:]
        avg = sum(recent) / len(recent)

        return round(avg, 2)

    def calculate_runway_months(
        self, current_balance: float, monthly_burn_rate: float
    ) -> float:
        """
        Calculate runway in months based on current balance and burn rate.

        Args:
            current_balance: Current cash balance
            monthly_burn_rate: Average monthly cash out

        Returns:
            Number of months of runway
        """
        if monthly_burn_rate <= 0:
            return float("inf")  # Infinite runway if no burn

        runway = Decimal(str(current_balance)) / Decimal(str(monthly_burn_rate))

        return float(round(runway, 1))

    # ============================================
    # Helper Methods
    # ============================================

    def _calculate_vp(self, parcelas: List[Dict[str, Any]], ref_date: date) -> float:
        """
        Calculate VP from parcelas using vlr_presente field from API.

        The API Mega already:
        - Sets vlr_presente=0 for paid installments
        - Sets vlr_presente=0 for inactive/overdue installments
        - Sets vlr_presente>0 only for active receivable installments

        So we just sum all vlr_presente values without additional filtering.
        """
        vp = Decimal("0")

        for parcela in parcelas:
            # VP já vem calculado pela API Mega com todos os filtros aplicados
            vlr_presente = self._parse_decimal(parcela.get("vlr_presente", 0))
            vp += vlr_presente

        return float(vp)

    def _calculate_prazo_medio(self, contratos: List[Dict[str, Any]], parcelas: Optional[List[Dict[str, Any]]] = None) -> float:
        """
        Calculate weighted average term.

        If prazo_meses is not available in contracts, extract from parcelas 'sequencia' field.
        Example sequencia: "001/120" means 120 total months.
        """
        if not contratos:
            return 0.0

        total_value = Decimal("0")
        weighted_sum = Decimal("0")

        for contrato in contratos:
            if not self.config.is_contrato_ativo(contrato.get("status_contrato")):
                continue

            prazo = self._parse_decimal(contrato.get("prazo_meses", 0))
            valor = self._parse_decimal(contrato.get("valor_contrato", 0))

            if prazo > 0 and valor > 0:
                weighted_sum += prazo * valor
                total_value += valor

        # If no prazo info found in contracts, extract from parcelas' sequencia field
        if weighted_sum == 0 and parcelas:
            from collections import defaultdict

            # Extract prazo from sequencia field (e.g., "001/120" -> 120 months)
            prazo_por_contrato = {}

            for parcela in parcelas:
                cod_contrato = parcela.get("cod_contrato")
                if not cod_contrato or cod_contrato in prazo_por_contrato:
                    continue  # Skip if already found prazo for this contract

                # Only consider "Mensal" parcelas to avoid counting "Sinal" (001/001)
                tipo_parcela = parcela.get("tipo_parcela", "")
                if tipo_parcela != "Mensal":
                    continue

                sequencia = parcela.get("sequencia", "")
                if "/" in str(sequencia):
                    try:
                        # Extract total from "001/120" format
                        parts = str(sequencia).split("/")
                        if len(parts) == 2:
                            total_parcelas = int(parts[1])
                            prazo_por_contrato[cod_contrato] = total_parcelas
                    except (ValueError, IndexError):
                        pass

            # Now calculate weighted prazo for each contract
            for contrato in contratos:
                if not self.config.is_contrato_ativo(contrato.get("status_contrato")):
                    continue

                cod_contrato = contrato.get("cod_contrato")
                valor = self._parse_decimal(contrato.get("valor_contrato", 0))

                if cod_contrato and cod_contrato in prazo_por_contrato and valor > 0:
                    prazo_meses = Decimal(str(prazo_por_contrato[cod_contrato]))
                    weighted_sum += prazo_meses * valor
                    total_value += valor

        if total_value > 0:
            return float(round(weighted_sum / total_value, 1))

        return 0.0

    def _parse_decimal(self, value: Any) -> Decimal:
        """Parse value to Decimal."""
        if value is None:
            return Decimal("0")

        if isinstance(value, Decimal):
            return value

        if isinstance(value, (int, float)):
            return Decimal(str(value))

        if isinstance(value, str):
            cleaned = value.replace(",", "").replace(" ", "").strip()
            try:
                return Decimal(cleaned)
            except:
                return Decimal("0")

        return Decimal("0")

    def _parse_date(self, value: Any) -> Optional[date]:
        """Parse value to date."""
        if value is None:
            return None

        if isinstance(value, date):
            return value

        if isinstance(value, datetime):
            return value.date()

        if isinstance(value, str):
            formats = [
                "%Y-%m-%d",
                "%d/%m/%Y",
                "%Y-%m-%dT%H:%M:%S",
                "%Y-%m-%dT%H:%M:%S.%f",
            ]

            for fmt in formats:
                try:
                    return datetime.strptime(value, fmt).date()
                except ValueError:
                    continue

        return None
