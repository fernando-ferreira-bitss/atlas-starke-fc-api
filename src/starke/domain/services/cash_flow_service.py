"""Cash flow calculation service with business rules."""

from datetime import date
from decimal import Decimal
from typing import Any, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from starke.core.logging import get_logger
from starke.domain.entities.cash_flow import (
    BalanceData,
    CashInCategory,
    CashInData,
    CashOutCategory,
    CashOutData,
    DelinquencyData,
    PortfolioStatsData,
)
from starke.domain.entities.contracts import ParcelaData
from starke.domain.services.portfolio_calculator import PortfolioCalculator
from starke.infrastructure.database.models import CashIn, CashOut, PortfolioStats

logger = get_logger(__name__)


class CashFlowService:
    """Service for calculating cash flow metrics and applying business rules."""

    def __init__(self, session: Session) -> None:
        """
        Initialize cash flow service.

        Args:
            session: Database session
        """
        self.session = session
        self.portfolio_calculator = PortfolioCalculator()

    def calculate_cash_in_from_parcelas(
        self,
        parcelas: list[dict[str, Any]],
        empreendimento_id: int,
        empreendimento_nome: str,
        ref_date: date,
    ) -> list[CashInData]:
        """
        Calculate cash inflows from installment data.

        Business Rules (Updated):
        - Filter by parcela_origem IN ('Contrato', 'Tabela Price') - others go to OUTRAS
        - FORECAST: Boletos with vencimento in ref_month AND status_parcela = "Ativo"
        - ACTUAL: Boletos with data_baixa in ref_month AND status_parcela = "Ativo" AND situacao = "Pago"

        Categories (based on parcela_origem and payment timing):
        - ATIVOS: Paid in same month/year as vencimento (parcela_origem = Contrato/Tabela Price)
        - RECUPERACOES: Paid after vencimento month (parcela_origem = Contrato/Tabela Price)
        - ANTECIPACOES: Paid before vencimento month (parcela_origem = Contrato/Tabela Price)
        - OUTRAS: All other parcela_origem types (Renegociação, Reajuste, Termo Contratual, etc)

        Args:
            parcelas: List of installment data from API
            empreendimento_id: Empreendimento ID
            empreendimento_nome: Empreendimento name
            ref_date: Reference date (last day of month)

        Returns:
            List of CashInData by category
        """
        ref_month_str = f"{ref_date.year}-{ref_date.month:02d}"
        ref_month = ref_date.month
        ref_year = ref_date.year

        logger.info(
            "Calculating cash inflows with parcela_origem filter",
            empreendimento_id=empreendimento_id,
            ref_month=ref_month_str,
            parcela_count=len(parcelas),
        )

        # Initialize accumulators by category
        categories = {
            CashInCategory.ATIVOS: {"forecast": Decimal("0"), "actual": Decimal("0")},
            CashInCategory.RECUPERACOES: {"forecast": Decimal("0"), "actual": Decimal("0")},
            CashInCategory.ANTECIPACOES: {"forecast": Decimal("0"), "actual": Decimal("0")},
            CashInCategory.OUTRAS: {"forecast": Decimal("0"), "actual": Decimal("0")},
        }

        for parcela_dict in parcelas:
            try:
                # Get status_parcela (cadastro status)
                status_parcela = str(parcela_dict.get("status_parcela") or "")

                # Only process "Ativo" parcelas (case-insensitive)
                if status_parcela.lower() != "ativo":
                    continue

                # Check parcela_origem - filter for Contrato/Tabela Price
                parcela_origem = str(parcela_dict.get("parcela_origem") or "")
                is_contract_origin = parcela_origem in ("Contrato", "Tabela Price")

                # Parse data_vencimento (due date)
                data_venc_str = parcela_dict.get("data_vencimento") or parcela_dict.get("dataVencimento")
                if not data_venc_str:
                    continue

                data_venc = self._parse_date(data_venc_str)
                if not data_venc:
                    continue

                # Get values
                valor_original = Decimal(str(
                    parcela_dict.get("vlr_original") or
                    parcela_dict.get("vlr_corrigido") or
                    0
                ))
                valor_pago = Decimal(str(
                    parcela_dict.get("vlr_pago") or
                    parcela_dict.get("valorPago") or
                    0
                ))

                # FORECAST: Vencimento in reference month
                venc_in_month = (data_venc.month == ref_month and data_venc.year == ref_year)

                if venc_in_month:
                    # If not contract origin, goes to OUTRAS
                    if not is_contract_origin:
                        forecast_category = CashInCategory.OUTRAS
                    else:
                        # For contract origin, default to ATIVOS in forecast
                        forecast_category = CashInCategory.ATIVOS

                    categories[forecast_category]["forecast"] += valor_original

                # ACTUAL: Payment (data_baixa) in reference month
                # Parse data_baixa (payment date)
                data_baixa_str = parcela_dict.get("data_baixa") or parcela_dict.get("dataBaixa")
                data_baixa = self._parse_date(data_baixa_str) if data_baixa_str else None

                # Get situacao (payment status)
                situacao = str(parcela_dict.get("situacao") or "").lower()

                # Check if paid in reference month
                if data_baixa and data_baixa.month == ref_month and data_baixa.year == ref_year:
                    # Only count if situacao is "Pago"
                    if situacao in ("pago", "liquidado", "quitado"):
                        # If not contract origin, goes to OUTRAS
                        if not is_contract_origin:
                            actual_category = CashInCategory.OUTRAS
                        else:
                            # For contract origin, classify by payment timing
                            # Compare month/year of payment vs vencimento
                            venc_month_year = (data_venc.year, data_venc.month)
                            baixa_month_year = (data_baixa.year, data_baixa.month)

                            if baixa_month_year < venc_month_year:
                                # Paid before vencimento month = antecipação
                                actual_category = CashInCategory.ANTECIPACOES
                            elif baixa_month_year > venc_month_year:
                                # Paid after vencimento month = recuperação
                                actual_category = CashInCategory.RECUPERACOES
                            else:
                                # Paid in same month/year as vencimento = ativo
                                actual_category = CashInCategory.ATIVOS

                        categories[actual_category]["actual"] += valor_pago

            except Exception as e:
                logger.warning(
                    "Error processing installment for cash in",
                    parcela=parcela_dict,
                    error=str(e),
                )

        # Create CashInData objects
        cash_in_list = []
        for category, values in categories.items():
            cash_in = CashInData(
                empreendimento_id=empreendimento_id,
                empreendimento_nome=empreendimento_nome,
                ref_date=ref_date,
                category=category,
                forecast=values["forecast"],
                actual=values["actual"],
            )
            cash_in_list.append(cash_in)

            logger.debug(
                "Cash in calculated",
                category=category.value,
                forecast=float(values["forecast"]),
                actual=float(values["actual"]),
            )

        return cash_in_list

    def _parse_date(self, date_str: str) -> Optional[date]:
        """
        Parse date from various formats.

        Args:
            date_str: Date string in DD/MM/YYYY or ISO format

        Returns:
            Parsed date or None if invalid
        """
        if not date_str or date_str == "null":
            return None

        try:
            if "/" in date_str:  # DD/MM/YYYY
                day, month, year = date_str.split("/")
                return date(int(year), int(month), int(day))
            elif "-" in date_str:  # ISO format YYYY-MM-DD
                return date.fromisoformat(date_str.split("T")[0])
        except Exception as e:
            logger.warning(f"Failed to parse date: {date_str}", error=str(e))
            return None

        return None

    def calculate_cash_out_from_despesas(
        self,
        despesas: list[dict[str, Any]],
        contratos: list[dict[str, Any]],
        empreendimento_id: int,
        empreendimento_nome: str,
        ref_date: date,
        mapper: Optional[Any] = None,
    ) -> list[CashOutData]:
        """
        Calculate cash outflows from despesas (contas a pagar).

        Business Rules (Updated):
        - Uses TipoDocumento from API directly as category
        - No longer uses ClasseFinanceira mapping or old categories (OPEX, CAPEX, etc.)
        - Examples of TipoDocumento: "NF_REF", "NF SERV", etc.
        - If TipoDocumento is missing, uses "OUTROS"
        - Filters despesas by empreendimento using Agente.Codigo -> Contrato lookup

        Args:
            despesas: List of despesas dictionaries from API (all despesas, not filtered)
            contratos: List of contratos for empreendimento lookup (cod_contrato -> empreendimento_id)
            empreendimento_id: ID of the empreendimento to filter
            empreendimento_nome: Name of the empreendimento
            ref_date: Reference date for calculations
            mapper: DEPRECATED - No longer used

        Returns:
            List of CashOutData objects grouped by TipoDocumento
        """
        ref_month = ref_date.month
        ref_year = ref_date.year

        # Create mapping: cod_contrato -> empreendimento_id
        contrato_to_emp: dict[int, int] = {}
        for contrato in contratos:
            cod_contrato = contrato.get("cod_contrato")
            emp_id = contrato.get("empreendimento_id") or contrato.get("cod_empreendimento")
            if cod_contrato and emp_id:
                contrato_to_emp[int(cod_contrato)] = int(emp_id)

        # Group by TipoDocumento (category)
        categories: dict[str, dict[str, float]] = {}

        logger.info(
            "Calculating cash out from despesas (using TipoDocumento)",
            despesas_count=len(despesas),
            ref_month=f"{ref_year}-{ref_month:02d}",
            empreendimento_id=empreendimento_id,
            contratos_mapped=len(contrato_to_emp),
        )

        filtered_count = 0
        skipped_count = 0

        for despesa_dict in despesas:
            try:
                # Filter by empreendimento using Agente.Codigo -> Contrato lookup
                agente = despesa_dict.get("Agente", {})
                agente_codigo = agente.get("Codigo") if isinstance(agente, dict) else None

                if agente_codigo:
                    despesa_emp_id = contrato_to_emp.get(int(agente_codigo))

                    if despesa_emp_id is None:
                        # Agente.Codigo exists but not found in contratos mapping
                        logger.info(
                            "Despesa skipped: Agente.Codigo not found in contratos mapping",
                            agente_codigo=agente_codigo,
                            tipo_documento=despesa_dict.get("TipoDocumento"),
                            valor_parcela=despesa_dict.get("ValorParcela"),
                        )
                        skipped_count += 1
                        continue

                    # Skip if not from this empreendimento
                    if despesa_emp_id != empreendimento_id:
                        skipped_count += 1
                        continue
                else:
                    # No Agente.Codigo - skip (can't determine empreendimento)
                    logger.info(
                        "Despesa skipped: No Agente.Codigo found",
                        tipo_documento=despesa_dict.get("TipoDocumento"),
                        valor_parcela=despesa_dict.get("ValorParcela"),
                    )
                    skipped_count += 1
                    continue

                # Parse data_vencimento (due date)
                data_venc_str = despesa_dict.get("DataVencimento") or despesa_dict.get("data_vencimento")
                if not data_venc_str:
                    continue

                data_venc = self._parse_date(data_venc_str)
                if not data_venc:
                    continue

                # Get valor (amount)
                valor_parcela = float(despesa_dict.get("ValorParcela") or despesa_dict.get("valor_parcela") or 0)
                if valor_parcela <= 0:
                    continue

                # Get saldo atual (current balance)
                saldo_atual = float(despesa_dict.get("SaldoAtual") or despesa_dict.get("saldo_atual") or 0)

                filtered_count += 1

                # Get TipoDocumento (NEW: use directly as category)
                tipo_documento = str(
                    despesa_dict.get("TipoDocumento")
                    or despesa_dict.get("tipo_documento")
                    or "OUTROS"
                ).strip()

                # Initialize category if not exists
                if tipo_documento not in categories:
                    categories[tipo_documento] = {"budget": 0.0, "actual": 0.0}

                # FORECAST: Parcelas with vencimento in reference month
                venc_in_month = (data_venc.month == ref_month and data_venc.year == ref_year)

                if venc_in_month:
                    # Budget = valor total da parcela
                    categories[tipo_documento]["budget"] += valor_parcela

                # ACTUAL: Parcelas pagas (SaldoAtual = 0) with vencimento in reference month
                # Assuming payment happens on due date for paid items
                if saldo_atual == 0 and venc_in_month:
                    # Actual = valor pago (total menos saldo)
                    valor_pago = valor_parcela - saldo_atual
                    categories[tipo_documento]["actual"] += valor_pago

            except Exception as e:
                logger.warning(
                    "Error processing despesa",
                    error=str(e),
                    despesa=despesa_dict,
                )
                continue

        # Create CashOutData objects
        cash_out_list: list[CashOutData] = []
        for tipo_documento, values in categories.items():
            cash_out_list.append(
                CashOutData(
                    empreendimento_id=empreendimento_id,
                    empreendimento_nome=empreendimento_nome,
                    ref_date=ref_date,
                    category=tipo_documento,  # TipoDocumento used directly
                    budget=Decimal(str(values["budget"])),
                    actual=Decimal(str(values["actual"])),
                )
            )

        logger.info(
            "Cash out calculation completed",
            tipo_documento_count=len(cash_out_list),
            categories=list(categories.keys()),
            total_budget=sum(c.budget for c in cash_out_list),
            total_actual=sum(c.actual for c in cash_out_list),
            filtered_despesas=filtered_count,
            skipped_despesas=skipped_count,
        )

        return cash_out_list

    def calculate_portfolio_stats(
        self,
        contratos: list[dict[str, Any]],
        empreendimento_id: int,
        empreendimento_nome: str,
        ref_date: date,
        parcelas: Optional[list[dict[str, Any]]] = None,
    ) -> PortfolioStatsData:
        """
        Calculate portfolio statistics from contract and parcela data.

        VP Carteira Calculation (Updated):
        - If parcelas provided: Sum vlr_presente from parcelas where:
          * status_parcela = 'Ativo'
          * data_baixa IS NULL (not paid)
          * parcela_origem IN ('Contrato', 'Tabela Price')
        - If parcelas not provided: Fallback to contract valor (old behavior)

        Args:
            contratos: List of contract data
            empreendimento_id: Empreendimento ID
            empreendimento_nome: Empreendimento name
            ref_date: Reference date
            parcelas: Optional list of parcela data for accurate VP calculation

        Returns:
            Portfolio statistics
        """
        logger.info(
            "Calculating portfolio stats",
            empreendimento_id=empreendimento_id,
            ref_date=ref_date.isoformat(),
            contract_count=len(contratos),
            parcela_count=len(parcelas) if parcelas else 0,
        )

        total_contracts = len(contratos)
        active_contracts = 0
        total_vp = Decimal("0")
        total_ltv = Decimal("0")
        total_prazo = Decimal("0")
        total_duration = Decimal("0")
        total_receivable = Decimal("0")

        # Count active contracts
        for contrato in contratos:
            status = str(contrato.get("status", "")).lower()
            if status in ("ativo", "vigente", "normal"):
                active_contracts += 1

        # Calculate VP from parcelas if available (NEW BEHAVIOR)
        if parcelas:
            logger.info("Calculating VP from parcelas using vlr_presente field")
            vp_parcela_count = 0

            for parcela_dict in parcelas:
                try:
                    # Filter criteria for VP:
                    # 1. status_parcela = 'Ativo'
                    status_parcela = str(parcela_dict.get("status_parcela") or "")
                    if status_parcela.lower() != "ativo":
                        continue

                    # 2. data_baixa IS NULL (not paid)
                    data_baixa = parcela_dict.get("data_baixa") or parcela_dict.get("dataBaixa")
                    if data_baixa:
                        continue  # Skip paid parcelas

                    # 3. parcela_origem IN ('Contrato', 'Tabela Price')
                    parcela_origem = str(parcela_dict.get("parcela_origem") or "")
                    if parcela_origem not in ("Contrato", "Tabela Price"):
                        continue

                    # Get vlr_presente (present value)
                    vlr_presente = Decimal(str(
                        parcela_dict.get("vlr_presente") or
                        parcela_dict.get("valorPresente") or
                        0
                    ))

                    if vlr_presente > 0:
                        total_vp += vlr_presente
                        vp_parcela_count += 1

                except Exception as e:
                    logger.warning(
                        "Error processing parcela for VP calculation",
                        parcela=parcela_dict,
                        error=str(e),
                    )

            logger.info(
                "VP calculated from parcelas",
                total_vp=float(total_vp),
                parcela_count=vp_parcela_count,
            )

        # Fallback: Calculate from contratos (OLD BEHAVIOR)
        else:
            logger.warning("Calculating VP from contratos (fallback - not ideal)")
            for contrato in contratos:
                valor_contrato = Decimal(str(contrato.get("valorContrato", 0) or contrato.get("valor_contrato", 0)))
                saldo_devedor = Decimal(str(contrato.get("saldoDevedor", 0) or contrato.get("saldo_devedor", 0)))

                total_vp += valor_contrato
                total_receivable += saldo_devedor

        # Calculate advanced metrics using PortfolioCalculator
        # (LTV, prazo médio, duration)
        avg_ltv = Decimal("0")
        avg_prazo = Decimal("0")
        avg_duration = Decimal("0")

        if parcelas and contratos:
            try:
                logger.info("Using PortfolioCalculator for advanced metrics")
                advanced_stats = self.portfolio_calculator.calculate_portfolio_stats(
                    contratos=contratos,
                    parcelas=parcelas,
                    ref_date=ref_date,
                )

                # Extract calculated values (keep VP from our calculation, use others from calculator)
                avg_ltv = Decimal(str(advanced_stats.get("ltv", 0)))
                avg_prazo = Decimal(str(advanced_stats.get("prazo_medio", 0)))
                avg_duration = Decimal(str(advanced_stats.get("duration", 0)))

                logger.info(
                    "Advanced metrics calculated",
                    ltv=float(avg_ltv),
                    prazo_medio=float(avg_prazo),
                    duration=float(avg_duration),
                )
            except Exception as e:
                logger.warning(
                    "Failed to calculate advanced metrics, using defaults",
                    error=str(e),
                )
        else:
            logger.warning(
                "Skipping advanced metrics calculation - missing data",
                has_parcelas=parcelas is not None,
                has_contratos=len(contratos) > 0 if contratos else False,
            )

        stats = PortfolioStatsData(
            empreendimento_id=empreendimento_id,
            empreendimento_nome=empreendimento_nome,
            ref_date=ref_date,
            vp=total_vp,
            ltv=avg_ltv,
            prazo_medio=avg_prazo,
            duration=avg_duration,
            total_contracts=total_contracts,
            active_contracts=active_contracts,
            total_receivable=total_receivable,
        )

        logger.info(
            "Portfolio stats calculated",
            vp=float(stats.vp),
            total_contracts=stats.total_contracts,
            active_contracts=stats.active_contracts,
        )

        return stats

    def calculate_delinquency_from_parcelas(
        self,
        parcelas: list[dict[str, Any]],
        empreendimento_id: int,
        empreendimento_nome: str,
        ref_date: date,
    ) -> DelinquencyData:
        """
        Calculate delinquency aging buckets from parcelas.

        Business Rules (UPDATED):
        - IMPORTANT: If ref_date > today, cap ref_date to today to prevent
          miscalculating aging buckets for installments overdue today but not
          yet overdue at the future ref_date
        - Filter by status_parcela = 'Ativo'
        - Filter by parcela_origem IN ('Contrato', 'Tabela Price')
        - Filter by data_vencimento < date.today() (already due in reality)
        - Filter by data_vencimento < ref_date (already due in reference period)
        - Filter by maximum aging (skip parcelas > 365 days overdue to prevent
          impossible aging from data migration errors)
        - Calculate dias_atraso:
          * If unpaid (data_baixa is NULL): ref_date - data_vencimento
          * If paid before/on ref_date (data_baixa <= ref_date): data_baixa - data_vencimento
          * If paid after ref_date (data_baixa > ref_date): ref_date - data_vencimento
        - Only consider parcelas with dias_atraso > 0 (overdue)
        - Use vlr_original (not vlr_presente which is 0 for paid parcelas)
        - Classify by aging buckets:
          * 0-30 days
          * 30-60 days
          * 60-90 days
          * 90-180 days
          * >180 days (capped at max 365 days total aging)
        - Track both VALUES and QUANTITIES for each bucket

        Args:
            parcelas: List of parcelas from Datawarehouse API
            empreendimento_id: Empreendimento ID
            empreendimento_nome: Empreendimento name
            ref_date: Reference date for calculation (capped to today if future)

        Returns:
            DelinquencyData with aging buckets and quantities in details
        """
        today = date.today()  # Current system date

        # IMPORTANT: If ref_date is in the future, cap it to today
        # This prevents miscalculating aging buckets for installments that are
        # overdue today but wouldn't be overdue yet at the future ref_date
        original_ref_date = ref_date
        if ref_date > today:
            ref_date = today
            logger.info(
                f"ref_date ({original_ref_date}) is in the future, capping to today ({today})"
            )

        logger.info(
            "Calculating delinquency",
            empreendimento_id=empreendimento_id,
            ref_date=ref_date.isoformat(),
            hoje=today.isoformat(),
            total_parcelas=len(parcelas),
        )

        # Initialize aging buckets (values)
        aging_values = {
            "up_to_30": Decimal("0"),
            "days_30_60": Decimal("0"),
            "days_60_90": Decimal("0"),
            "days_90_180": Decimal("0"),
            "above_180": Decimal("0"),
        }

        # Initialize aging buckets (quantities)
        aging_quantities = {
            "up_to_30": 0,
            "days_30_60": 0,
            "days_60_90": 0,
            "days_90_180": 0,
            "above_180": 0,
        }

        processed_count = 0
        overdue_count = 0
        skipped_future = 0
        skipped_not_due = 0
        skipped_too_old = 0

        # Maximum reasonable aging for a parcela (in days)
        # We cap this at 365 days to prevent impossible aging buckets
        # from data migration issues or system errors
        MAX_REASONABLE_AGING_DAYS = 365

        for parcela_dict in parcelas:
            # Filter 1: Check parcela_origem
            parcela_origem = str(parcela_dict.get("parcela_origem") or "")
            if parcela_origem not in ("Contrato", "Tabela Price"):
                continue

            # Filter 2: Check status_parcela
            status_parcela = str(parcela_dict.get("status_parcela") or "")
            if status_parcela.lower() != "ativo":
                continue

            # Parse data_vencimento
            data_venc_value = parcela_dict.get("data_vencimento")
            if not data_venc_value:
                logger.warning(
                    "Parcela without data_vencimento",
                    parcela_id=parcela_dict.get("cod_parcela"),
                )
                continue

            data_vencimento = self._parse_date(str(data_venc_value)) if data_venc_value else None
            if not data_vencimento:
                continue

            # Filter 3: Parcela must be already due in REALITY (not future)
            if data_vencimento >= today:
                skipped_future += 1
                continue

            # Filter 4: Parcela must be already due in REFERENCE PERIOD
            if data_vencimento >= ref_date:
                skipped_not_due += 1
                continue

            # Filter 5: Skip parcelas with unreasonably old vencimento dates
            # This prevents data migration errors or system glitches from creating
            # impossible aging buckets (e.g., >180 days when development is only 150 days old)
            potential_dias_atraso = (ref_date - data_vencimento).days
            if potential_dias_atraso > MAX_REASONABLE_AGING_DAYS:
                skipped_too_old += 1
                # Silently skip - count is reported in final summary
                continue

            # Parse data_baixa (payment date)
            data_baixa_str = parcela_dict.get("data_baixa") or parcela_dict.get("dataBaixa")
            data_baixa = self._parse_date(data_baixa_str) if data_baixa_str else None

            # Calculate dias_atraso based on payment status
            if data_baixa is None:
                # Case A: Unpaid - calculate from ref_date
                dias_atraso = (ref_date - data_vencimento).days
            elif data_baixa <= ref_date:
                # Case B1: Paid before/on ref_date - use actual payment delay
                dias_atraso = (data_baixa - data_vencimento).days
            else:
                # Case B2: Paid after ref_date - calculate as if still unpaid at ref_date
                dias_atraso = (ref_date - data_vencimento).days

            # Only consider overdue parcelas (paid late or still unpaid late)
            # Skip if not overdue OR if within 3-day compensation period
            if dias_atraso < 3:
                continue

            processed_count += 1
            overdue_count += 1

            # Get parcela value - ALWAYS use vlr_original (not vlr_presente!)
            valor = Decimal(
                str(
                    parcela_dict.get("vlr_original")
                    or parcela_dict.get("vlr_corrigido")
                    or 0
                )
            )

            # Classify by aging bucket
            # Note: Only process parcelas with 3+ days overdue (after bank compensation period)
            if dias_atraso <= 30:
                aging_values["up_to_30"] += valor
                aging_quantities["up_to_30"] += 1
            elif dias_atraso <= 60:
                aging_values["days_30_60"] += valor
                aging_quantities["days_30_60"] += 1
            elif dias_atraso <= 90:
                aging_values["days_60_90"] += valor
                aging_quantities["days_60_90"] += 1
            elif dias_atraso <= 180:
                aging_values["days_90_180"] += valor
                aging_quantities["days_90_180"] += 1
            else:
                # dias_atraso > 180
                aging_values["above_180"] += valor
                aging_quantities["above_180"] += 1

        # Calculate totals
        total_value = sum(aging_values.values())
        total_quantity = sum(aging_quantities.values())

        # Create delinquency data
        delinquency = DelinquencyData(
            empreendimento_id=empreendimento_id,
            empreendimento_nome=empreendimento_nome,
            ref_date=ref_date,
            up_to_30=aging_values["up_to_30"],
            days_30_60=aging_values["days_30_60"],
            days_60_90=aging_values["days_60_90"],
            days_90_180=aging_values["days_90_180"],
            above_180=aging_values["above_180"],
            total=total_value,
            details={
                "quantities": {
                    "up_to_30": aging_quantities["up_to_30"],
                    "days_30_60": aging_quantities["days_30_60"],
                    "days_60_90": aging_quantities["days_60_90"],
                    "days_90_180": aging_quantities["days_90_180"],
                    "above_180": aging_quantities["above_180"],
                    "total": total_quantity,
                },
                "filters": {
                    "parcela_origem": ["Contrato", "Tabela Price"],
                    "status_parcela": "Ativo",
                },
            },
        )

        logger.info(
            "Delinquency calculated",
            total_value=float(total_value),
            total_quantity=total_quantity,
            overdue_count=overdue_count,
            processed_count=processed_count,
            skipped_future=skipped_future,
            skipped_not_due=skipped_not_due,
            skipped_too_old=skipped_too_old,
        )

        return delinquency

    def calculate_balance(
        self,
        cash_in_list: list[CashInData],
        cash_out_list: list[CashOutData],
        empreendimento_id: int,
        empreendimento_nome: str,
        ref_date: date,
        opening_balance: Optional[Decimal] = None,
    ) -> BalanceData:
        """
        Calculate cash balance.

        Args:
            cash_in_list: List of cash inflows
            cash_out_list: List of cash outflows
            empreendimento_id: Empreendimento ID
            empreendimento_nome: Empreendimento name
            ref_date: Reference date
            opening_balance: Opening balance (if None, fetch from previous period)

        Returns:
            Balance data
        """
        logger.info(
            "Calculating balance",
            empreendimento_id=empreendimento_id,
            ref_date=ref_date.isoformat(),
        )

        # Calculate totals
        total_in = sum(ci.actual for ci in cash_in_list)
        total_out = sum(co.actual for co in cash_out_list)

        # Get opening balance (from previous period if not provided)
        if opening_balance is None:
            opening_balance = self._get_previous_closing_balance(
                empreendimento_id, ref_date
            )

        # Calculate closing balance
        closing_balance = opening_balance + total_in - total_out

        balance = BalanceData(
            empreendimento_id=empreendimento_id,
            empreendimento_nome=empreendimento_nome,
            ref_date=ref_date,
            opening=opening_balance,
            closing=closing_balance,
            total_in=total_in,
            total_out=total_out,
        )

        logger.info(
            "Balance calculated",
            opening=float(balance.opening),
            closing=float(balance.closing),
            net_flow=float(balance.net_flow),
        )

        return balance

    def _get_previous_closing_balance(
        self, empreendimento_id: int, ref_date: date
    ) -> Decimal:
        """
        Get closing balance from previous month.

        Args:
            empreendimento_id: Empreendimento ID
            ref_date: Current reference date

        Returns:
            Previous closing balance or 0
        """
        # Get previous month in YYYY-MM format
        if ref_date.month == 1:
            prev_month_str = f"{ref_date.year - 1}-12"
        else:
            prev_month_str = f"{ref_date.year}-{ref_date.month - 1:02d}"

        stmt = (
            select(Balance)
            .where(
                Balance.empreendimento_id == empreendimento_id,
                Balance.ref_month == prev_month_str,
            )
            .order_by(Balance.created_at.desc())
            .limit(1)
        )

        result = self.session.execute(stmt).scalar_one_or_none()

        if result:
            return Decimal(str(result.closing))

        logger.warning(
            "No previous balance found, using 0",
            empreendimento_id=empreendimento_id,
            prev_month=prev_month_str,
        )
        return Decimal("0")

    def save_cash_flow_data(
        self,
        cash_in_list: list[CashInData],
        cash_out_list: list[CashOutData],
        balance: BalanceData,
        portfolio_stats: Optional[PortfolioStatsData] = None,
    ) -> None:
        """
        Save calculated cash flow data to database using UPSERT.

        This function uses PostgreSQL's INSERT ... ON CONFLICT DO UPDATE
        to update existing records or insert new ones (monthly aggregation).

        Args:
            cash_in_list: List of cash inflows
            cash_out_list: List of cash outflows
            balance: Balance data
            portfolio_stats: Portfolio statistics (optional)
        """
        from sqlalchemy.dialects.postgresql import insert

        ref_month = f"{cash_in_list[0].ref_date.year}-{cash_in_list[0].ref_date.month:02d}"

        logger.info(
            "Saving cash flow data to database (UPSERT)",
            ref_month=ref_month,
            cash_in_count=len(cash_in_list),
            cash_out_count=len(cash_out_list),
        )

        # UPSERT cash inflows
        for cash_in in cash_in_list:
            stmt = insert(CashIn).values(
                empreendimento_id=cash_in.empreendimento_id,
                empreendimento_nome=cash_in.empreendimento_nome,
                ref_month=ref_month,
                category=cash_in.category.value,
                forecast=float(cash_in.forecast),
                actual=float(cash_in.actual),
                details=cash_in.details,
            )

            # On conflict, update the values
            stmt = stmt.on_conflict_do_update(
                constraint='uq_cash_in_emp_month_category',
                set_={
                    'empreendimento_nome': stmt.excluded.empreendimento_nome,
                    'forecast': stmt.excluded.forecast,
                    'actual': stmt.excluded.actual,
                    'details': stmt.excluded.details,
                }
            )

            self.session.execute(stmt)

        # UPSERT cash outflows
        for cash_out in cash_out_list:
            stmt = insert(CashOut).values(
                empreendimento_id=cash_out.empreendimento_id,
                empreendimento_nome=cash_out.empreendimento_nome,
                ref_month=ref_month,
                category=cash_out.category.value,
                budget=float(cash_out.budget),
                actual=float(cash_out.actual),
                details=cash_out.details,
            )

            stmt = stmt.on_conflict_do_update(
                constraint='uq_cash_out_emp_month_category',
                set_={
                    'empreendimento_nome': stmt.excluded.empreendimento_nome,
                    'budget': stmt.excluded.budget,
                    'actual': stmt.excluded.actual,
                    'details': stmt.excluded.details,
                }
            )

            self.session.execute(stmt)

        # UPSERT balance
        stmt = insert(Balance).values(
            empreendimento_id=balance.empreendimento_id,
            empreendimento_nome=balance.empreendimento_nome,
            ref_month=ref_month,
            opening=float(balance.opening),
            closing=float(balance.closing),
            details=balance.details,
        )

        stmt = stmt.on_conflict_do_update(
            constraint='uq_balance_emp_month',
            set_={
                'empreendimento_nome': stmt.excluded.empreendimento_nome,
                'opening': stmt.excluded.opening,
                'closing': stmt.excluded.closing,
                'details': stmt.excluded.details,
            }
        )

        self.session.execute(stmt)

        # UPSERT portfolio stats (only if provided)
        if portfolio_stats:
            stmt = insert(PortfolioStats).values(
                empreendimento_id=portfolio_stats.empreendimento_id,
                empreendimento_nome=portfolio_stats.empreendimento_nome,
                ref_month=ref_month,
                vp=float(portfolio_stats.vp),
                ltv=float(portfolio_stats.ltv),
                prazo_medio=float(portfolio_stats.prazo_medio),
                duration=float(portfolio_stats.duration),
                total_contracts=portfolio_stats.total_contracts,
                active_contracts=portfolio_stats.active_contracts,
                details=portfolio_stats.details,
            )

            stmt = stmt.on_conflict_do_update(
                constraint='uq_portfolio_emp_month',
                set_={
                    'empreendimento_nome': stmt.excluded.empreendimento_nome,
                    'vp': stmt.excluded.vp,
                    'ltv': stmt.excluded.ltv,
                    'prazo_medio': stmt.excluded.prazo_medio,
                    'duration': stmt.excluded.duration,
                    'total_contracts': stmt.excluded.total_contracts,
                    'active_contracts': stmt.excluded.active_contracts,
                    'details': stmt.excluded.details,
                }
            )

            self.session.execute(stmt)

        self.session.flush()
        logger.info("Cash flow data saved successfully (UPSERT)")
