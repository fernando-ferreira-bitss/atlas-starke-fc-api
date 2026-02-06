"""Transform Mega API data to Starke domain models."""

import logging
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple

from starke.core.config_loader import get_mega_config
from starke.core.date_helpers import utc_now

logger = logging.getLogger(__name__)


class MegaDataTransformer:
    """Transform data from Mega API format to Starke domain models."""

    def __init__(self):
        """Initialize transformer with configuration."""
        self.config = get_mega_config()

    # ============================================
    # Development (Empreendimento)
    # ============================================

    def transform_empreendimento(self, mega_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Transform Mega empreendimento to Starke Development format.

        Args:
            mega_data: Raw empreendimento data from Mega API

        Returns:
            Dict with Development model fields
        """
        # Extract ID and name from API response
        emp_id = mega_data.get("codigo")
        emp_name = mega_data.get("nome") or mega_data.get("descricao") or f"Empreendimento {emp_id}"

        # Status - consider active only if field is 'A'
        # Default to False, will be set to True later if development has active contracts
        status = mega_data.get("status")
        is_active = status == "A" if status else False

        # Extract nested data if available
        # Filial can be either a direct field or nested object
        filial_codigo = mega_data.get("codigoFilial")
        if not filial_codigo and "filial" in mega_data and isinstance(mega_data["filial"], dict):
            filial_codigo = mega_data["filial"].get("codigo")

        # Centro custo and projeto are nested objects
        centro_custo = None
        if "centroCusto" in mega_data and isinstance(mega_data["centroCusto"], dict):
            centro_custo = mega_data["centroCusto"].get("reduzido")

        projeto = None
        if "projeto" in mega_data and isinstance(mega_data["projeto"], dict):
            projeto = mega_data["projeto"].get("reduzido")

        return {
            "external_id": int(emp_id),  # Original ID from Mega API
            "name": emp_name,
            "is_active": is_active,
            "raw_data": mega_data,  # Store complete raw data
            "last_synced_at": utc_now(),
            # Metadata for filtering/querying
            "_filial_codigo": filial_codigo,
            "_centro_custo": centro_custo,
            "_projeto": projeto,
        }

    # ============================================
    # Contract (Contrato)
    # ============================================

    def transform_contrato(
        self, contrato: Dict[str, Any], empreendimento_id: int, empreendimento_nome: str
    ) -> Dict[str, Any]:
        """
        Transform Mega contrato to Starke Contract format.

        Args:
            contrato: Raw contrato data from Mega API (via get_contratos)
            empreendimento_id: ID of the development
            empreendimento_nome: Name of the development

        Returns:
            Dict with Contract model fields
        """
        # Extract contract code from API response
        cod_contrato = contrato.get("cod_contrato")

        if not cod_contrato:
            raise ValueError(f"Contract missing cod_contrato: {contrato}")

        # Extract status
        status = contrato.get("status_contrato")

        # Extract valor_contrato
        valor_contrato = contrato.get("valor_contrato")
        if valor_contrato is not None:
            try:
                valor_contrato = Decimal(str(valor_contrato))
            except (ValueError, TypeError):
                valor_contrato = None

        # Extract data_assinatura
        data_assinatura = None
        data_assinatura_str = contrato.get("data_assinatura")
        if data_assinatura_str:
            try:
                # API may return date in ISO format or DD/MM/YYYY
                if "/" in data_assinatura_str:
                    data_assinatura = datetime.strptime(data_assinatura_str, "%d/%m/%Y").date()
                else:
                    data_assinatura = datetime.fromisoformat(data_assinatura_str.split("T")[0]).date()
            except (ValueError, TypeError) as e:
                logger.warning(f"Failed to parse data_assinatura: {data_assinatura_str}: {e}")

        return {
            "cod_contrato": int(cod_contrato),
            "empreendimento_id": empreendimento_id,
            "status": status,
            "valor_contrato": valor_contrato,
            "valor_atualizado_ipca": None,  # Will be calculated later if needed
            "data_assinatura": data_assinatura,
            "last_synced_at": utc_now(),
        }

    # ============================================
    # Cash In - Parcelas de Contratos
    # ============================================

    def transform_parcela_to_cash_in(
        self,
        parcela: Dict[str, Any],
        empreendimento_id: int,
        empreendimento_nome: str,
        contract_data: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Transform Mega parcela (installment) to Starke CashIn records.

        Creates two records:
        1. Forecast record (based on due date)
        2. Actual record (based on payment date, if paid)

        Args:
            parcela: Raw parcela data from Mega API
            empreendimento_id: ID of the development
            empreendimento_nome: Name of the development
            contract_data: Optional contract data for additional context

        Returns:
            List of CashIn dicts (1 or 2 records)
        """
        records = []

        # Extract values from API response
        # From /api/Carteira/DadosParcelas/IdContrato={id}
        valor_original = self._parse_decimal(parcela.get("vlr_original", 0))
        valor_realizado = self._parse_decimal(parcela.get("vlr_pago", 0))
        dt_vencimento = self._parse_date(parcela.get("data_vencimento"))
        dt_pagamento = self._parse_date(parcela.get("data_baixa"))

        # Get IDs from API response
        parcela_id = parcela.get("cod_parcela")
        contrato_id = parcela.get("cod_contrato")

        # Forecast record (on due date)
        if dt_vencimento and valor_original > 0:
            records.append(
                {
                    "empreendimento_id": empreendimento_id,
                    "empreendimento_nome": empreendimento_nome,
                    "ref_month": dt_vencimento.strftime("%Y-%m"),  # YYYY-MM format
                    "ref_date": dt_vencimento.isoformat(),  # Full date for filtering
                    "category": "ativos",  # Revenue from assets (contracts)
                    "forecast": float(valor_original),
                    "actual": 0.0,
                    "details": {
                        "parcela_id": parcela_id,
                        "contrato_id": contrato_id,
                        "tipo": "forecast",
                        "vencimento": dt_vencimento.isoformat(),
                    },
                }
            )

        # Actual record (on payment date)
        if dt_pagamento and valor_realizado > 0:
            records.append(
                {
                    "empreendimento_id": empreendimento_id,
                    "empreendimento_nome": empreendimento_nome,
                    "ref_month": dt_pagamento.strftime("%Y-%m"),  # YYYY-MM format
                    "ref_date": dt_pagamento.isoformat(),  # Full date for filtering
                    "category": "ativos",
                    "forecast": 0.0,
                    "actual": float(valor_realizado),
                    "details": {
                        "parcela_id": parcela_id,
                        "contrato_id": contrato_id,
                        "tipo": "actual",
                        "vencimento": dt_vencimento.isoformat() if dt_vencimento else None,
                        "pagamento": dt_pagamento.isoformat(),
                    },
                }
            )

        return records

    # ============================================
    # Cash Out - Despesas
    # ============================================

    def transform_fatura_pagar_to_cash_out(
        self, fatura: Dict[str, Any], empreendimento_id: int, empreendimento_nome: str
    ) -> List[Dict[str, Any]]:
        """
        Transform Mega fatura a pagar to Starke CashOut records.

        Uses data from /api/FinanceiroMovimentacao/FaturaPagar/Saldo endpoint.
        This endpoint only provides budget/forecast data, not actual payment data.

        Creates 1 budget record per fatura based on due date (DataVencimento).
        Category is determined from TipoDocumento field.

        Args:
            fatura: Raw fatura data from Mega API Saldo endpoint (PascalCase format)
            empreendimento_id: ID of the development
            empreendimento_nome: Name of the development

        Returns:
            List with 1 CashOut dict (budget record only)
        """
        records = []

        # Extract values from Saldo endpoint format (PascalCase)
        # API: /api/FinanceiroMovimentacao/FaturaPagar/Saldo
        # This endpoint only provides budget/forecast data, not actual payment data

        # Use TipoDocumento as category (e.g., "DISTRATO", "NOTA FISCAL", etc.)
        tipo_documento = fatura.get("TipoDocumento", "OUTROS")
        category = self.config.get_cash_out_category(tipo_documento) if tipo_documento else "outras"

        valor_parcela = self._parse_decimal(fatura.get("ValorParcela"))
        dt_vencimento = self._parse_date(fatura.get("DataVencimento"))  # Format: DD/MM/YYYY

        # Get IDs and metadata from Saldo format
        numero_ap = fatura.get("NumeroAP")
        numero_documento = fatura.get("NumeroDocumento")
        numero_parcela = fatura.get("NumeroParcela")

        agente = fatura.get("Agente", {})
        agente_codigo = agente.get("Codigo") if isinstance(agente, dict) else None
        agente_nome = agente.get("Nome") if isinstance(agente, dict) else None

        logger.debug(
            f"Processing cash_out fatura: tipo={tipo_documento}, dt_vencimento={dt_vencimento}, "
            f"valor_parcela={valor_parcela}, agente={agente_codigo}"
        )

        if not dt_vencimento or not valor_parcela or valor_parcela <= 0:
            logger.warning(f"Skipping fatura with missing or invalid data: {numero_documento}")
            return records

        # Create budget record (on due date)
        # Saldo endpoint only provides budget/forecast data, not actual payment data
        records.append(
            {
                "empreendimento_id": empreendimento_id,
                "empreendimento_nome": empreendimento_nome,
                "ref_month": dt_vencimento.strftime('%Y-%m'),
                "category": category,
                "budget": float(valor_parcela),
                "actual": 0.0,
                "details": {
                    "numero_ap": numero_ap,
                    "numero_documento": numero_documento,
                    "numero_parcela": numero_parcela,
                    "tipo_documento": tipo_documento,
                    "agente_codigo": agente_codigo,
                    "agente_nome": agente_nome,
                    "vencimento": dt_vencimento.isoformat(),
                },
            }
        )

        return records

    def transform_fatura_pagar(self, fatura: Dict[str, Any]) -> Dict[str, Any]:
        """
        Transform Mega fatura a pagar to Starke FaturaPagar model.

        Uses data from /api/FinanceiroMovimentacao/FaturaPagar/Saldo endpoint.
        This endpoint provides invoice data with current balance (saldo).

        Args:
            fatura: Raw fatura data from Mega API Saldo endpoint (PascalCase format)
                Expected structure:
                {
                    "Filial": {"Id": 10301, "Nome": "GREEN VILLAGE"},
                    "NumeroAP": "921",
                    "NumeroParcela": "011",
                    "TipoDocumento": "DISTRATO",
                    "NumeroDocumento": "000001",
                    "ValorParcela": 10000.0,
                    "SaldoAtual": 0.0,  # 0 if paid
                    "DataVencimento": "30/10/2025",
                    "Agente": {"Codigo": 8245, "Nome": "FORNECEDOR XYZ"}
                }

        Returns:
            Dict with FaturaPagar model fields (without data_baixa - that's set during sync)
        """
        # Extract filial data
        filial = fatura.get("Filial", {})
        filial_id = filial.get("Id") if isinstance(filial, dict) else None
        filial_nome = filial.get("Nome") if isinstance(filial, dict) else None

        if not filial_id:
            raise ValueError(f"Fatura missing Filial.Id: {fatura}")

        # Extract invoice identifiers
        numero_ap = str(fatura.get("NumeroAP", ""))
        numero_parcela = str(fatura.get("NumeroParcela", ""))

        if not numero_ap or not numero_parcela:
            raise ValueError(f"Fatura missing NumeroAP or NumeroParcela: {fatura}")

        # Extract document info
        tipo_documento = fatura.get("TipoDocumento", "OUTROS")
        numero_documento = fatura.get("NumeroDocumento")

        # Extract financial data
        valor_parcela = self._parse_decimal(fatura.get("ValorParcela"))
        saldo_atual = self._parse_decimal(fatura.get("SaldoAtual", 0))

        # Extract dates
        data_vencimento = self._parse_date(fatura.get("DataVencimento"))

        if not data_vencimento:
            raise ValueError(f"Fatura missing DataVencimento: {fatura}")

        # Extract agent data
        agente = fatura.get("Agente", {})
        agente_codigo = agente.get("Codigo") if isinstance(agente, dict) else None
        agente_nome = agente.get("Nome") if isinstance(agente, dict) else None

        return {
            "origem": "mega",
            "filial_id": int(filial_id),
            "filial_nome": filial_nome or f"Filial {filial_id}",
            "numero_ap": numero_ap,
            "numero_parcela": numero_parcela,
            "tipo_documento": tipo_documento,
            "numero_documento": numero_documento,
            "valor_parcela": valor_parcela,
            "saldo_atual": saldo_atual,
            "data_vencimento": data_vencimento,
            "agente_codigo": agente_codigo,
            "agente_nome": agente_nome,
            "dados_brutos": fatura,
            # data_baixa will be set during sync based on business logic
        }

    # ============================================
    # Balance - Saldo de Caixa
    # ============================================

    def transform_saldo_to_balance(
        self, saldo: Dict[str, Any], empreendimento_id: int, empreendimento_nome: str, ref_date: date
    ) -> Optional[Dict[str, Any]]:
        """
        Transform Mega saldo contábil to Starke Balance.

        Args:
            saldo: Raw saldo data from Mega API
            empreendimento_id: ID of the development
            empreendimento_nome: Name of the development
            ref_date: Reference date for the balance

        Returns:
            Balance dict or None if account is not a cash/bank account
        """
        # Check if this is a cash/bank account
        conta_codigo = saldo.get("conta", {}).get("codigo") if isinstance(saldo.get("conta"), dict) else None

        if not conta_codigo or not self.config.is_conta_disponibilidade(conta_codigo):
            return None  # Not a cash account, skip

        # Extract balance values
        saldo_inicial = self._parse_decimal(saldo.get("saldoInicial", 0))
        debitos = self._parse_decimal(saldo.get("debitos", 0))
        creditos = self._parse_decimal(saldo.get("creditos", 0))
        saldo_final = self._parse_decimal(saldo.get("saldoFinal", 0))

        # Calculate opening and closing (accounting convention may vary)
        # Typically: Saldo Final = Saldo Inicial + Débitos - Créditos
        opening = float(saldo_inicial)
        closing = float(saldo_final)

        return {
            "empreendimento_id": empreendimento_id,
            "empreendimento_nome": empreendimento_nome,
            "ref_date": ref_date.isoformat(),
            "opening": opening,
            "closing": closing,
            "details": {
                "conta_codigo": conta_codigo,
                "conta_descricao": saldo.get("conta", {}).get("descricao"),
                "saldo_inicial": opening,
                "debitos": float(debitos),
                "creditos": float(creditos),
                "saldo_final": closing,
            },
        }

    # ============================================
    # Helper Methods
    # ============================================

    def _parse_decimal(self, value: Any) -> Decimal:
        """Parse value to Decimal, handling None and various formats."""
        if value is None:
            return Decimal("0")

        if isinstance(value, Decimal):
            return value

        if isinstance(value, (int, float)):
            return Decimal(str(value))

        if isinstance(value, str):
            # Remove common formatting
            cleaned = value.replace(",", "").replace(" ", "").strip()
            try:
                return Decimal(cleaned)
            except:
                logger.warning(f"Could not parse decimal from: {value}")
                return Decimal("0")

        return Decimal("0")

    def _parse_date(self, value: Any) -> Optional[date]:
        """Parse value to date, handling various formats."""
        if value is None:
            return None

        if isinstance(value, date):
            return value

        if isinstance(value, datetime):
            return value.date()

        if isinstance(value, str):
            # Try common formats
            formats = [
                "%Y-%m-%d",  # ISO format
                "%d/%m/%Y",  # Brazilian format
                "%Y-%m-%dT%H:%M:%S",  # ISO datetime
                "%Y-%m-%dT%H:%M:%S.%f",  # ISO datetime with microseconds
            ]

            for fmt in formats:
                try:
                    return datetime.strptime(value, fmt).date()
                except ValueError:
                    continue

            logger.warning(f"Could not parse date from: {value}")

        return None

    def _safe_get_nested(self, data: Dict[str, Any], *keys: str, default: Any = None) -> Any:
        """Safely get nested dictionary value."""
        current = data
        for key in keys:
            if not isinstance(current, dict):
                return default
            current = current.get(key)
            if current is None:
                return default
        return current
