"""UAU API synchronization service - orchestrates data import from UAU to Starke."""

import logging
from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy.orm import Session

from starke.domain.services.uau_transformer import UAUDataTransformer
from starke.infrastructure.external_apis.uau_api_client import UAUAPIClient
from starke.core.date_helpers import utc_now

logger = logging.getLogger(__name__)


class UAUSyncService:
    """Service to synchronize data from UAU API to Starke database.

    UAU API structure:
    - Empresa = Empreendimento (Development)
    - Obra = Fase (grouped by Empresa)
    - Venda = Contrato
    - Parcela = Installments

    Note: UAU Filial IDs use an offset to avoid collision with Mega Filial IDs.
    """

    # Offset para evitar colisão de IDs entre Mega e UAU na tabela filiais
    UAU_FILIAL_ID_OFFSET = 1_000_000

    def __init__(self, db: Session, api_client: Optional[UAUAPIClient] = None):
        """
        Initialize sync service.

        Args:
            db: Database session
            api_client: Optional UAU API client (creates new one if not provided)
        """
        self.db = db
        self.api_client = api_client
        self.transformer = UAUDataTransformer()
        self._client_owned = api_client is None

    def __enter__(self):
        """Context manager entry."""
        if self._client_owned:
            self.api_client = UAUAPIClient()
            self.api_client.__enter__()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        if self._client_owned and self.api_client:
            self.api_client.__exit__(exc_type, exc_val, exc_tb)

    # ============================================
    # Empresas (Developments) Synchronization
    # ============================================

    def sync_empresas(self) -> int:
        """
        Synchronize empresas from UAU API as developments and filiais.

        In UAU, each Empresa becomes:
        - 1 Filial (for CashOut aggregation)
        - 1 Development (for CashIn and PortfolioStats)

        Returns:
            Number of empresas synchronized
        """
        from starke.infrastructure.database.models import Development, Filial

        logger.info("Starting UAU empresas synchronization")

        try:
            # Fetch empresas from UAU API
            empresas = self.api_client.get_empresas()
            logger.info(f"Found {len(empresas)} empresas in UAU API")

            # === OPTIMIZATION: Load all existing records in ONE query each ===
            # Instead of 280 queries (2 per empresa), we do just 2 queries total
            existing_filiais = (
                self.db.query(Filial)
                .filter(Filial.origem == "uau")
                .all()
            )
            existing_devs = (
                self.db.query(Development)
                .filter(Development.origem == "uau")
                .all()
            )

            # Create lookup dictionaries by external_id for O(1) access
            filiais_by_external_id = {f.external_id: f for f in existing_filiais}
            devs_by_external_id = {d.external_id: d for d in existing_devs}

            logger.info(f"Loaded {len(filiais_by_external_id)} existing filiais and {len(devs_by_external_id)} existing developments")

            now = utc_now()

            count = 0
            for empresa in empresas:
                try:
                    # Transform to Starke format
                    transformed = self.transformer.transform_empresa_to_development(empresa)
                    external_empresa_id = transformed["external_id"]  # Original ID from UAU API
                    empresa_name = transformed["name"]

                    # === 1. Create/Update Filial ===
                    existing_filial = filiais_by_external_id.get(external_empresa_id)

                    if existing_filial:
                        existing_filial.nome = empresa_name
                        # NOTE: Do NOT update is_active - user controls activation via API
                        existing_filial.atualizado_em = now
                        filial_internal_id = existing_filial.id
                    else:
                        new_filial = Filial(
                            external_id=external_empresa_id,
                            nome=empresa_name,
                            is_active=transformed["is_active"],
                            origem="uau",
                        )
                        self.db.add(new_filial)
                        self.db.flush()  # Get the auto-generated id
                        filial_internal_id = new_filial.id
                        filiais_by_external_id[external_empresa_id] = new_filial  # Add to cache
                        logger.info(f"Created filial UAU: {empresa_name} (external_id: {external_empresa_id})")

                    # === 2. Create/Update Development ===
                    existing_dev = devs_by_external_id.get(external_empresa_id)

                    if existing_dev:
                        existing_dev.name = empresa_name
                        existing_dev.filial_id = filial_internal_id  # Link to Filial (internal id)
                        # NOTE: Do NOT update is_active - user controls activation via API
                        existing_dev.raw_data = transformed["raw_data"]
                        existing_dev.last_synced_at = transformed["last_synced_at"]
                        existing_dev.updated_at = now
                    else:
                        new_dev = Development(
                            external_id=external_empresa_id,
                            name=empresa_name,
                            filial_id=filial_internal_id,  # Link to Filial (internal id)
                            is_active=transformed["is_active"],
                            raw_data=transformed["raw_data"],
                            origem="uau",
                            last_synced_at=transformed["last_synced_at"],
                        )
                        self.db.add(new_dev)
                        devs_by_external_id[external_empresa_id] = new_dev  # Add to cache
                        logger.info(f"Created empresa: {empresa_name} (external_id: {external_empresa_id})")

                    count += 1

                except Exception as e:
                    logger.error(f"Error processing empresa {empresa.get('Codigo_emp', 'UNKNOWN')}: {e}")
                    continue

            self.db.commit()
            logger.info(f"Successfully synchronized {count} empresas from UAU (as Filial + Development)")
            return count

        except Exception as e:
            logger.error(f"Error synchronizing empresas: {e}")
            self.db.rollback()
            raise

    # ============================================
    # Vendas (Contracts) Synchronization
    # ============================================

    def sync_vendas(
        self,
        empresa_id: int,
        data_inicio: str,
        data_fim: str,
        dev: Optional[Any] = None,
    ) -> int:
        """
        Synchronize vendas (contracts) for an empresa.

        Uses cache strategy: finalized vendas (Cancelada, Quitada) are not re-fetched
        from the API since their data won't change.

        Args:
            empresa_id: Empresa ID (external_id in UAU)
            data_inicio: Start date in "YYYY-MM-DD" format
            data_fim: End date in "YYYY-MM-DD" format
            dev: Optional pre-loaded Development object

        Returns:
            Number of contracts synchronized
        """
        from starke.infrastructure.database.models import Contract, Development

        logger.info(f"Syncing vendas for empresa {empresa_id} ({data_inicio} to {data_fim})")

        try:
            # Get development for this empresa
            if dev is None:
                dev = self.db.query(Development).filter(
                    Development.external_id == empresa_id,
                    Development.origem == "uau"
                ).first()

            if not dev:
                logger.warning(f"Development not found for empresa external_id={empresa_id}")
                return 0

            empreendimento_internal_id = dev.id

            # === CACHE STRATEGY ===
            # Load existing UAU contracts for this empresa that are finalized (Cancelada, Quitada)
            # These don't need to be re-fetched from the API
            existing_contracts = (
                self.db.query(Contract)
                .filter(
                    Contract.empreendimento_id == empreendimento_internal_id,
                    Contract.origem == "uau",
                )
                .all()
            )

            # Build set of finalized vendas (empresa, obra, numero) to exclude from API fetch
            # Format must match api_client's _parse_venda_key: (empresa, obra, numero)
            finalized_vendas = set()
            for contract in existing_contracts:
                if contract.status in ("Cancelada", "Quitada"):
                    # empresa_id is the external UAU ID, stored in Development.external_id
                    finalized_vendas.add((empresa_id, contract.obra, contract.cod_contrato))

            logger.info(
                f"Found {len(existing_contracts)} existing contracts, "
                f"{len(finalized_vendas)} finalized (will be skipped)"
            )

            # Fetch vendas from API (excluding finalized ones)
            vendas = self.api_client.exportar_vendas_por_periodo(
                empresa=empresa_id,
                data_inicio=data_inicio,
                data_fim=data_fim,
                exclude_vendas=finalized_vendas,
            )

            logger.info(f"Fetched {len(vendas)} vendas from API (after cache exclusion)")

            if not vendas:
                return 0

            # Build lookup for existing contracts by (obra, cod_contrato)
            contracts_by_key = {
                (c.obra, c.cod_contrato): c for c in existing_contracts
            }

            # === Fetch IPCA data ONCE for all contracts ===
            from datetime import datetime
            from decimal import Decimal

            ipca_data = {}
            try:
                from starke.domain.services.ipca_service import IPCAService

                # Find earliest signing date among active contracts
                active_contracts_dates = []
                for venda in vendas:
                    status_code = str(venda.get("StatusVenda", "0"))
                    # Active statuses: 0=Normal, 4=Em acerto
                    if status_code in ("0", "4"):
                        data_venda_str = venda.get("DataDaVenda")
                        if data_venda_str:
                            try:
                                data_venda = datetime.strptime(data_venda_str, "%Y-%m-%d").date()
                                active_contracts_dates.append(data_venda)
                            except Exception:
                                continue

                if active_contracts_dates:
                    earliest_date = min(active_contracts_dates)
                    ipca_service = IPCAService()
                    ipca_data = ipca_service.fetch_ipca_data(earliest_date, date.today())
                    logger.info(f"Fetched IPCA data from {earliest_date} to today ({len(ipca_data)} months)")
                else:
                    logger.info("No active contracts with signing dates, skipping IPCA fetch")

            except Exception as e:
                logger.error(f"Failed to fetch IPCA data: {e}")

            # Transform and upsert vendas
            count = 0
            for venda in vendas:
                try:
                    # Transform venda to contract format
                    contract_data = self.transformer.transform_venda_to_contract(
                        venda, empreendimento_internal_id
                    )

                    if not contract_data:
                        continue

                    obra = contract_data["obra"]
                    cod_contrato = contract_data["cod_contrato"]
                    key = (obra, cod_contrato)

                    # === Calculate IPCA-adjusted value for ACTIVE contracts ===
                    valor_atualizado_ipca = None
                    status = contract_data.get("status")
                    data_assinatura = contract_data.get("data_assinatura")
                    valor_contrato = contract_data.get("valor_contrato")

                    # Active statuses: Normal, Em acerto
                    is_active = status in ("Normal", "Em acerto")

                    if is_active and ipca_data and data_assinatura and valor_contrato:
                        try:
                            # Calculate first month to apply IPCA (month AFTER signing)
                            year = data_assinatura.year
                            month = data_assinatura.month + 1
                            if month > 12:
                                month = 1
                                year += 1
                            first_correction_month = date(year, month, 1)

                            # Calculate accumulated IPCA from month after signing
                            accumulated = Decimal("1")
                            for month_key in sorted(ipca_data.keys()):
                                month_date = datetime.strptime(month_key + "-01", "%Y-%m-%d").date()
                                if month_date >= first_correction_month:
                                    ipca_monthly = ipca_data[month_key]
                                    accumulated *= (Decimal("1") + ipca_monthly / Decimal("100"))

                            # Calculate adjusted value
                            accumulated_percentage = (accumulated - Decimal("1")) * Decimal("100")
                            valor_atualizado_ipca = Decimal(str(valor_contrato)) * (Decimal("1") + accumulated_percentage / Decimal("100"))

                            logger.debug(
                                f"Calculated IPCA for contract {obra}/{cod_contrato}: "
                                f"R$ {float(valor_contrato):,.2f} → R$ {float(valor_atualizado_ipca):,.2f} "
                                f"({float(accumulated_percentage):.2f}% accumulated)"
                            )
                        except Exception as e:
                            logger.error(f"Failed to calculate IPCA for contract {obra}/{cod_contrato}: {e}")

                    # Check if contract exists
                    existing = contracts_by_key.get(key)

                    if existing:
                        # Update existing contract
                        existing.status = contract_data["status"]
                        existing.valor_contrato = contract_data["valor_contrato"]
                        existing.valor_atualizado_ipca = valor_atualizado_ipca
                        existing.data_assinatura = contract_data["data_assinatura"]
                        existing.cliente_cpf = contract_data["cliente_cpf"]
                        existing.cliente_codigo = contract_data["cliente_codigo"]
                        existing.last_synced_at = contract_data["last_synced_at"]
                        logger.debug(f"Updated contract: {key}")
                    else:
                        # Create new contract
                        new_contract = Contract(
                            cod_contrato=cod_contrato,
                            empreendimento_id=empreendimento_internal_id,
                            obra=obra,
                            origem="uau",
                            status=contract_data["status"],
                            valor_contrato=contract_data["valor_contrato"],
                            valor_atualizado_ipca=valor_atualizado_ipca,
                            data_assinatura=contract_data["data_assinatura"],
                            cliente_cpf=contract_data["cliente_cpf"],
                            cliente_codigo=contract_data["cliente_codigo"],
                            last_synced_at=contract_data["last_synced_at"],
                        )
                        self.db.add(new_contract)
                        contracts_by_key[key] = new_contract  # Add to cache
                        logger.debug(f"Created contract: {key}")

                    count += 1

                except Exception as e:
                    logger.error(f"Error processing venda {venda.get('Numero')}: {e}")
                    continue

            self.db.commit()
            logger.info(f"Synchronized {count} contracts for empresa {empresa_id}")
            return count

        except Exception as e:
            logger.error(f"Error syncing vendas for empresa {empresa_id}: {e}")
            self.db.rollback()
            raise

    # ============================================
    # CashOut Synchronization
    # ============================================

    def sync_cash_out(
        self,
        empresa_id: int,
        mes_inicial: str,
        mes_final: str,
        dev: Optional[Any] = None,  # Optional pre-loaded Development to avoid extra query
    ) -> int:
        """
        Synchronize CashOut (desembolsos) for an empresa.

        Args:
            empresa_id: Empresa ID (= empreendimento_id)
            mes_inicial: Start month in "MM/YYYY" format
            mes_final: End month in "MM/YYYY" format
            dev: Optional pre-loaded Development object (optimization)

        Returns:
            Number of CashOut records created
        """
        from starke.infrastructure.database.models import CashOut, Development

        try:
            # Use pre-loaded Development or fetch from DB
            if dev is None:
                dev = self.db.query(Development).filter(
                    Development.external_id == empresa_id,
                    Development.origem == "uau"
                ).first()

            if not dev:
                logger.warning(f"Development not found for empresa external_id={empresa_id}")
                return 0

            empresa_nome = dev.name
            filial_id = dev.filial_id  # Internal filial ID

            logger.info(f"Syncing CashOut for empresa {empresa_id} (filial_id={filial_id}) ({mes_inicial} to {mes_final})")

            # Fetch desembolsos for all obras of the empresa
            desembolsos = self.api_client.get_desembolso_empresa(
                empresa=empresa_id,
                mes_inicial=mes_inicial,
                mes_final=mes_final,
            )

            logger.info(f"Found {len(desembolsos)} desembolso records for empresa {empresa_id}")

            if not desembolsos:
                return 0

            # Transform and aggregate - use internal filial_id
            aggregated = self.transformer.transform_desembolso_to_cash_out(
                desembolsos, filial_id, empresa_nome
            )

            # Clear existing records for this empresa and period
            # Parse mes_inicial and mes_final to get ref_months
            months_to_delete = self._get_months_in_range(mes_inicial, mes_final)

            self.db.query(CashOut).filter(
                CashOut.filial_id == filial_id,
                CashOut.mes_referencia.in_(months_to_delete),
                CashOut.origem == "uau",
            ).delete(synchronize_session=False)

            # Insert new records
            count = 0
            for record_data in aggregated.values():
                cash_out = CashOut(**record_data)
                self.db.add(cash_out)
                count += 1

            self.db.commit()
            logger.info(f"Synchronized {count} CashOut records for empresa {empresa_id}")
            return count

        except Exception as e:
            logger.error(f"Error syncing CashOut for empresa {empresa_id}: {e}")
            self.db.rollback()
            raise

    # ============================================
    # CashIn Synchronization (Otimizado com ExportarVendas)
    # ============================================

    def sync_cash_in_and_delinquency_via_export(
        self,
        empresa_id: int,
        data_inicio: str,
        data_fim: str,
        dev: Optional[Any] = None,
    ) -> Tuple[int, int, List[Dict[str, Any]]]:
        """
        Synchronize CashIn AND Delinquency using ExportarVendasXml.

        OPTIMIZED: Single API batch call replaces 2×N individual calls:
        - Old: 2 calls per venda (BuscarParcelasAReceber + BuscarParcelasRecebidas)
        - New: 1 call per 50 vendas (ExportarVendasXml with embedded parcelas)

        This method processes vendas once and extracts:
        1. CashIn (forecast from open parcelas, actual from paid parcelas)
        2. Delinquency (overdue unpaid + paid late, with 3-day grace period)

        Args:
            empresa_id: Empresa ID (external_id from UAU)
            data_inicio: Start date in "YYYY-MM-DD" format
            data_fim: End date in "YYYY-MM-DD" format
            dev: Optional pre-loaded Development object

        Returns:
            Tuple of (cash_in_count, delinquency_count, vendas_list)
        """
        from starke.infrastructure.database.models import CashIn, Delinquency, Development

        logger.info(f"Syncing CashIn + Delinquency via ExportarVendas for empresa {empresa_id}")

        try:
            # Use pre-loaded Development or fetch from DB
            if dev is None:
                dev = self.db.query(Development).filter(
                    Development.external_id == empresa_id,
                    Development.origem == "uau"
                ).first()

            if not dev:
                logger.warning(f"Development not found for empresa external_id={empresa_id}")
                return 0, 0, []

            empresa_nome = dev.name
            empreendimento_internal_id = dev.id

            # === SINGLE API CALL: Fetch all vendas with embedded parcelas ===
            vendas = self.api_client.exportar_vendas_por_periodo(
                empresa=empresa_id,
                data_inicio=data_inicio,
                data_fim=data_fim,
            )

            logger.info(f"Fetched {len(vendas)} vendas via ExportarVendas (batch mode)")

            if not vendas:
                return 0, 0, []

            # Calculate months in requested period
            months_in_period = set(self._get_months_between_dates(data_inicio, data_fim))
            ref_date = datetime.strptime(data_fim, "%Y-%m-%d").date()

            # === Process vendas for CashIn ===
            all_cash_in = []

            for venda in vendas:
                # Skip cancelled vendas
                if venda.get("StatusVenda") == "1":
                    continue

                # Get obra and num_venda for origin_id
                obra = venda.get("Obra", "")
                num_venda = self.transformer._safe_int(venda.get("Numero")) or 0

                # Get parcelas from venda
                parcelas_data = venda.get("Parcelas", {})
                parcelas = parcelas_data.get("Parcela", [])

                # Normalize to list
                if isinstance(parcelas, dict):
                    parcelas = [parcelas]

                for parcela in parcelas:
                    records = self.transformer.transform_parcela_export_to_cash_in(
                        parcela, empreendimento_internal_id, empresa_nome, obra, num_venda
                    )
                    for record in records:
                        if record.get("ref_month") in months_in_period:
                            all_cash_in.append(record)

            logger.info(f"Processed {len(all_cash_in)} parcelas for CashIn within period")

            # Aggregate CashIn by (emp_id, ref_month, category)
            aggregated_cash_in = self.transformer.aggregate_cash_in(all_cash_in)

            # === DB Operations ===
            # Refresh DB connection before critical operations
            from sqlalchemy import text
            from dateutil.relativedelta import relativedelta

            try:
                self.db.execute(text("SELECT 1"))
            except Exception:
                logger.warning("DB connection lost, rolling back to refresh...")
                self.db.rollback()

            # Clear and insert CashIn records
            cash_in_count = 0
            if months_in_period:
                self.db.query(CashIn).filter(
                    CashIn.empreendimento_id == empreendimento_internal_id,
                    CashIn.ref_month.in_(list(months_in_period)),
                    CashIn.origem == "uau",
                ).delete(synchronize_session=False)

                for record_data in aggregated_cash_in.values():
                    cash_in = CashIn(**record_data)
                    self.db.add(cash_in)
                    cash_in_count += 1

            # === Process Delinquency for EACH month in period (same as Mega) ===
            delinquency_count = 0
            for ref_month_str in sorted(months_in_period):
                try:
                    year, month = map(int, ref_month_str.split("-"))
                    month_start = date(year, month, 1)
                    last_day_of_month = month_start + relativedelta(months=1) - relativedelta(days=1)
                    month_ref_date = min(last_day_of_month, date.today())

                    delinquency = self.transformer.transform_parcelas_export_to_delinquency(
                        vendas, empreendimento_internal_id, empresa_nome, month_ref_date
                    )
                    delinquency["ref_month"] = ref_month_str

                    self.db.query(Delinquency).filter(
                        Delinquency.empreendimento_id == empreendimento_internal_id,
                        Delinquency.ref_month == ref_month_str,
                        Delinquency.origem == "uau",
                    ).delete()

                    delinquency_record = Delinquency(**delinquency)
                    self.db.add(delinquency_record)
                    delinquency_count += 1
                except Exception as e:
                    logger.error(f"Error calculating Delinquency for {ref_month_str}: {e}")

            self.db.commit()

            logger.info(
                f"Synchronized via ExportarVendas: "
                f"{cash_in_count} CashIn records, "
                f"{delinquency_count} Delinquency records"
            )

            return cash_in_count, delinquency_count, vendas

        except Exception as e:
            logger.error(f"Error syncing via ExportarVendas for empresa {empresa_id}: {e}")
            self.db.rollback()
            raise

    def sync_cash_in_via_export(
        self,
        empresa_id: int,
        data_inicio: str,
        data_fim: str,
        vendas: Optional[List[Dict[str, Any]]] = None,
        dev: Optional[Any] = None,
    ) -> Tuple[int, List[Dict[str, Any]]]:
        """
        Synchronize CashIn using ExportarVendasXml (optimized).

        Args:
            empresa_id: Empresa ID (external_id from UAU)
            data_inicio: Start date in "YYYY-MM-DD" format
            data_fim: End date in "YYYY-MM-DD" format
            vendas: Optional pre-fetched vendas (to reuse from contracts sync)
            dev: Optional pre-loaded Development object

        Returns:
            Tuple of (cash_in_count, vendas_list)
        """
        from starke.infrastructure.database.models import CashIn, Development

        logger.info(f"Syncing CashIn via ExportarVendas for empresa {empresa_id}")

        try:
            if dev is None:
                dev = self.db.query(Development).filter(
                    Development.external_id == empresa_id,
                    Development.origem == "uau"
                ).first()

            if not dev:
                logger.warning(f"Development not found for empresa external_id={empresa_id}")
                return 0, []

            empresa_nome = dev.name
            empreendimento_internal_id = dev.id

            # Fetch vendas if not provided
            if vendas is None:
                vendas = self.api_client.exportar_vendas_por_periodo(
                    empresa=empresa_id,
                    data_inicio=data_inicio,
                    data_fim=data_fim,
                )

            logger.info(f"Processing {len(vendas)} vendas for CashIn")

            if not vendas:
                return 0, []

            months_in_period = set(self._get_months_between_dates(data_inicio, data_fim))

            # Process vendas
            all_cash_in = []
            for venda in vendas:
                if venda.get("StatusVenda") == "1":
                    continue

                obra = venda.get("Obra", "")
                num_venda = self.transformer._safe_int(venda.get("Numero")) or 0

                parcelas_data = venda.get("Parcelas", {})
                parcelas = parcelas_data.get("Parcela", [])

                if isinstance(parcelas, dict):
                    parcelas = [parcelas]

                for parcela in parcelas:
                    records = self.transformer.transform_parcela_export_to_cash_in(
                        parcela, empreendimento_internal_id, empresa_nome, obra, num_venda
                    )
                    for record in records:
                        if record.get("ref_month") in months_in_period:
                            all_cash_in.append(record)

            aggregated = self.transformer.aggregate_cash_in(all_cash_in)

            # Refresh DB connection
            from sqlalchemy import text
            try:
                self.db.execute(text("SELECT 1"))
            except Exception:
                self.db.rollback()

            # Clear and insert
            if months_in_period:
                self.db.query(CashIn).filter(
                    CashIn.empreendimento_id == empreendimento_internal_id,
                    CashIn.ref_month.in_(list(months_in_period)),
                    CashIn.origem == "uau",
                ).delete(synchronize_session=False)

            count = 0
            for record_data in aggregated.values():
                cash_in = CashIn(**record_data)
                self.db.add(cash_in)
                count += 1

            self.db.commit()
            logger.info(f"Synchronized {count} CashIn records via ExportarVendas")
            return count, vendas

        except Exception as e:
            logger.error(f"Error syncing CashIn via export for empresa {empresa_id}: {e}")
            self.db.rollback()
            raise

    def sync_delinquency_via_export(
        self,
        empresa_id: int,
        ref_date: date,
        vendas: Optional[List[Dict[str, Any]]] = None,
        dev: Optional[Any] = None,
    ) -> int:
        """
        Synchronize Delinquency using ExportarVendasXml (optimized).

        Args:
            empresa_id: Empresa ID
            ref_date: Reference date for calculation
            vendas: Optional pre-fetched vendas (to reuse)
            dev: Optional pre-loaded Development object

        Returns:
            1 if record created, 0 otherwise
        """
        from starke.infrastructure.database.models import Delinquency, Development

        logger.info(f"Syncing Delinquency via ExportarVendas for empresa {empresa_id}")

        try:
            if dev is None:
                dev = self.db.query(Development).filter(
                    Development.external_id == empresa_id,
                    Development.origem == "uau"
                ).first()

            if not dev:
                logger.warning(f"Empresa external_id={empresa_id} not found")
                return 0

            empreendimento_internal_id = dev.id

            # Fetch vendas if not provided
            if vendas is None:
                vendas = self.api_client.exportar_vendas_por_periodo(
                    empresa=empresa_id,
                    data_inicio="2000-01-01",
                    data_fim=ref_date.isoformat(),
                )

            logger.info(f"Processing {len(vendas)} vendas for Delinquency")

            # Transform
            delinquency = self.transformer.transform_parcelas_export_to_delinquency(
                vendas, empreendimento_internal_id, dev.name, ref_date
            )

            # Clear and insert
            ref_month_str = ref_date.strftime("%Y-%m")
            self.db.query(Delinquency).filter(
                Delinquency.empreendimento_id == empreendimento_internal_id,
                Delinquency.ref_month == ref_month_str,
                Delinquency.origem == "uau",
            ).delete()

            delinquency_record = Delinquency(**delinquency)
            self.db.add(delinquency_record)
            self.db.commit()

            logger.info(f"Saved Delinquency: Total={delinquency['total']:,.2f}")
            return 1

        except Exception as e:
            logger.error(f"Error syncing Delinquency via export: {e}")
            self.db.rollback()
            raise

    # ============================================
    # CashIn Synchronization (Legacy - BuscarParcelas)
    # ============================================

    def sync_cash_in(
        self,
        empresa_id: int,
        data_inicio: str,
        data_fim: str,
        parcelas_data: Optional[Dict[str, List[Dict[str, Any]]]] = None,
        dev: Optional[Any] = None,  # Optional pre-loaded Development to avoid extra query
    ) -> Tuple[int, Dict[str, List[Dict[str, Any]]]]:
        """
        Synchronize CashIn (parcelas) for an empresa.

        This method:
        1. Lists all vendas for the empresa in the period
        2. For each venda, fetches parcelas a receber and recebidas
        3. Aggregates into CashIn records

        Args:
            empresa_id: Empresa ID (= empreendimento_id)
            data_inicio: Start date in "YYYY-MM-DD" format
            data_fim: End date in "YYYY-MM-DD" format
            parcelas_data: Optional pre-fetched parcelas data (to avoid duplicate API calls)
            dev: Optional pre-loaded Development object (optimization)

        Returns:
            Tuple of (number of CashIn records created, parcelas_data dict)
        """
        from starke.infrastructure.database.models import CashIn, Development

        logger.info(f"Syncing CashIn for empresa {empresa_id} ({data_inicio} to {data_fim})")

        try:
            # Use pre-loaded Development or fetch from DB
            if dev is None:
                dev = self.db.query(Development).filter(
                    Development.external_id == empresa_id,
                    Development.origem == "uau"
                ).first()

            if not dev:
                logger.warning(f"Development not found for empresa external_id={empresa_id}")
                return 0, {}

            empresa_nome = dev.name
            empreendimento_internal_id = dev.id  # Internal ID for DB relations

            # Get all parcelas for empresa (if not pre-fetched)
            if parcelas_data is None:
                parcelas_data = self.api_client.get_all_parcelas_empresa(
                    empresa=empresa_id,
                    data_inicio=data_inicio,
                    data_fim=data_fim,
                )

            parcelas_a_receber = parcelas_data.get("a_receber", [])
            parcelas_recebidas = parcelas_data.get("recebidas", [])

            logger.info(
                f"Found {len(parcelas_a_receber)} parcelas a receber and "
                f"{len(parcelas_recebidas)} parcelas recebidas"
            )

            # Calculate the months in the requested period (only delete/insert these)
            months_in_period = set(self._get_months_between_dates(data_inicio, data_fim))
            logger.info(f"Period requested: {data_inicio} to {data_fim} ({len(months_in_period)} months)")

            # Transform parcelas (use internal empreendimento_id for DB storage)
            # Only include parcelas within the requested period
            all_cash_in = []

            for parcela in parcelas_a_receber:
                record = self.transformer.transform_parcela_a_receber_to_cash_in(
                    parcela, empreendimento_internal_id, empresa_nome
                )
                if record and record.get("ref_month") in months_in_period:
                    all_cash_in.append(record)

            for parcela in parcelas_recebidas:
                record = self.transformer.transform_parcela_recebida_to_cash_in(
                    parcela, empreendimento_internal_id, empresa_nome
                )
                if record and record.get("ref_month") in months_in_period:
                    all_cash_in.append(record)

            logger.info(f"Filtered {len(all_cash_in)} parcelas within requested period")

            # Aggregate by (emp_id, ref_month, category)
            aggregated = self.transformer.aggregate_cash_in(all_cash_in)

            # Refresh DB connection before critical operations (connection may have timed out during API calls)
            from sqlalchemy import text
            try:
                self.db.execute(text("SELECT 1"))
            except Exception:
                logger.warning("DB connection lost, rolling back to refresh...")
                self.db.rollback()

            # Clear existing records ONLY for the requested period (not all months from API response)
            if months_in_period:
                logger.info(f"Deleting existing CashIn records for {len(months_in_period)} months in requested period")
                self.db.query(CashIn).filter(
                    CashIn.empreendimento_id == empreendimento_internal_id,  # Use internal ID
                    CashIn.ref_month.in_(list(months_in_period)),
                    CashIn.origem == "uau",
                ).delete(synchronize_session=False)

            # Insert new records
            count = 0
            for record_data in aggregated.values():
                cash_in = CashIn(**record_data)
                self.db.add(cash_in)
                count += 1

            self.db.commit()
            logger.info(f"Synchronized {count} CashIn records for empresa {empresa_id}")
            return count, parcelas_data

        except Exception as e:
            logger.error(f"Error syncing CashIn for empresa {empresa_id}: {e}")
            self.db.rollback()
            raise

    # ============================================
    # Portfolio Stats Synchronization
    # ============================================

    def sync_portfolio_stats(
        self,
        empresa_id: int,
        ref_month: str,
        data_calculo: Optional[str] = None,
        dev: Optional[Any] = None,  # Optional pre-loaded Development to avoid extra query
        vendas_com_parcelas_a_receber: Optional[set] = None,  # Cache of vendas with parcelas a receber
    ) -> int:
        """
        Synchronize Portfolio Stats (VP) for an empresa.

        Uses ConsultarParcelasDaVenda which calculates VP automatically.

        Args:
            empresa_id: Empresa ID
            ref_month: Reference month (YYYY-MM)
            data_calculo: Calculation date (defaults to last day of ref_month)
            dev: Optional pre-loaded Development object (optimization)
            vendas_com_parcelas_a_receber: Optional set of venda keys that have parcelas a receber.
                Format: {(empresa, obra, num_venda), ...}
                If provided, only these vendas will be queried for VP (major optimization).

        Returns:
            1 if record created, 0 otherwise
        """
        from starke.infrastructure.database.models import PortfolioStats, Development

        logger.info(f"Syncing PortfolioStats for empresa {empresa_id} ({ref_month})")

        try:
            # Use pre-loaded Development or fetch from DB
            if dev is None:
                dev = self.db.query(Development).filter(
                    Development.external_id == empresa_id,
                    Development.origem == "uau"
                ).first()

            if not dev:
                logger.warning(f"Empresa external_id={empresa_id} not found in database")
                return 0

            empreendimento_internal_id = dev.id  # Internal ID for DB relations

            # Calculate data_calculo (last day of ref_month)
            if not data_calculo:
                year, month = map(int, ref_month.split("-"))
                if month == 12:
                    next_month = date(year + 1, 1, 1)
                else:
                    next_month = date(year, month + 1, 1)
                last_day = next_month - timedelta(days=1)
                data_calculo = last_day.strftime("%Y-%m-%d")

            # Get all VP parcelas using parallel requests
            # If we have a cache of vendas with parcelas a receber, only query those (optimization)
            all_parcelas_vp = self.api_client.get_all_parcelas_vp_empresa(
                empresa=empresa_id,
                data_calculo=data_calculo,
                vendas_com_parcelas_a_receber=vendas_com_parcelas_a_receber,
            )

            logger.info(f"Collected {len(all_parcelas_vp)} parcelas with VP")

            # Transform to PortfolioStats (use internal ID)
            stats = self.transformer.transform_parcelas_to_portfolio_stats(
                all_parcelas_vp, empreendimento_internal_id, dev.name, ref_month
            )

            # Refresh DB connection before critical operations (connection may have timed out during API calls)
            from sqlalchemy import text
            try:
                self.db.execute(text("SELECT 1"))
            except Exception:
                logger.warning("DB connection lost, rolling back to refresh...")
                self.db.rollback()

            # Clear existing record (use internal ID)
            self.db.query(PortfolioStats).filter(
                PortfolioStats.empreendimento_id == empreendimento_internal_id,
                PortfolioStats.ref_month == ref_month,
                PortfolioStats.origem == "uau",
            ).delete()

            # Insert new record
            portfolio_stats = PortfolioStats(**stats)
            self.db.add(portfolio_stats)
            self.db.commit()

            logger.info(
                f"Saved PortfolioStats for empresa {empresa_id}: "
                f"VP={stats['vp']:,.2f}"
            )
            return 1

        except Exception as e:
            logger.error(f"Error syncing PortfolioStats for empresa {empresa_id}: {e}")
            self.db.rollback()
            raise

    def sync_portfolio_stats_for_months(
        self,
        empresa_id: int,
        months: List[str],
        dev: Optional[Any] = None,
        vendas_com_parcelas_a_receber: Optional[set] = None,
    ) -> int:
        """
        Sync PortfolioStats for multiple months.

        VP is calculated ONCE (with current values) and saved for ALL months.
        This is more efficient than calling the API for each month.

        Args:
            empresa_id: Empresa ID
            months: List of months in YYYY-MM format
            dev: Optional pre-loaded Development object
            vendas_com_parcelas_a_receber: Optional set of venda keys for VP optimization

        Returns:
            Number of records saved
        """
        from starke.infrastructure.database.models import PortfolioStats, Development

        if not months:
            return 0

        logger.info(f"Syncing PortfolioStats for empresa {empresa_id} ({len(months)} months)")

        try:
            # Use pre-loaded Development or fetch from DB
            if dev is None:
                dev = self.db.query(Development).filter(
                    Development.external_id == empresa_id,
                    Development.origem == "uau"
                ).first()

            if not dev:
                logger.warning(f"Empresa external_id={empresa_id} not found in database")
                return 0

            empreendimento_internal_id = dev.id

            # Calculate data_calculo (today)
            today = date.today()
            data_calculo = today.strftime("%Y-%m-%d")

            # Get VP parcelas ONCE (this is the slow API call)
            all_parcelas_vp = self.api_client.get_all_parcelas_vp_empresa(
                empresa=empresa_id,
                data_calculo=data_calculo,
                vendas_com_parcelas_a_receber=vendas_com_parcelas_a_receber,
            )

            logger.info(f"Collected {len(all_parcelas_vp)} parcelas with VP")

            # Transform to PortfolioStats (calculated once, used for all months)
            stats = self.transformer.transform_parcelas_to_portfolio_stats(
                all_parcelas_vp, empreendimento_internal_id, dev.name, months[0]
            )

            # Refresh DB connection before critical operations
            from sqlalchemy import text
            try:
                self.db.execute(text("SELECT 1"))
            except Exception:
                logger.warning("DB connection lost, rolling back to refresh...")
                self.db.rollback()

            # Get current month to determine which records to update
            current_month = today.strftime("%Y-%m")

            # Get existing records for this empresa
            existing_months = set(
                row[0] for row in self.db.query(PortfolioStats.ref_month).filter(
                    PortfolioStats.empreendimento_id == empreendimento_internal_id,
                    PortfolioStats.ref_month.in_(months),
                    PortfolioStats.origem == "uau",
                ).all()
            )

            # Determine which months to process:
            # - Current month: always update
            # - Past months without record: insert
            # - Past months with record: skip (preserve historical data)
            months_to_insert = []
            months_to_update = []

            for ref_month in months:
                if ref_month == current_month:
                    # Current month: always update
                    months_to_update.append(ref_month)
                elif ref_month not in existing_months:
                    # Past month without record: insert
                    months_to_insert.append(ref_month)
                # else: past month with record - skip

            logger.info(
                f"PortfolioStats: {len(months_to_insert)} to insert, "
                f"{len(months_to_update)} to update, "
                f"{len(existing_months) - len(months_to_update)} preserved"
            )

            # Delete only records that will be updated (current month)
            if months_to_update:
                self.db.query(PortfolioStats).filter(
                    PortfolioStats.empreendimento_id == empreendimento_internal_id,
                    PortfolioStats.ref_month.in_(months_to_update),
                    PortfolioStats.origem == "uau",
                ).delete(synchronize_session=False)

            # Insert records for months that need it
            count = 0
            for ref_month in months_to_insert + months_to_update:
                portfolio_stats = PortfolioStats(
                    empreendimento_id=empreendimento_internal_id,
                    empreendimento_nome=dev.name,
                    ref_month=ref_month,
                    vp=stats["vp"],
                    ltv=stats["ltv"],
                    prazo_medio=stats["prazo_medio"],
                    duration=stats["duration"],
                    total_contracts=stats["total_contracts"],
                    active_contracts=stats["active_contracts"],
                    details=stats.get("details"),
                    origem="uau",
                )
                self.db.add(portfolio_stats)
                count += 1

            self.db.commit()

            logger.info(
                f"Saved {count} PortfolioStats records for empresa {empresa_id}: "
                f"VP={stats['vp']:,.2f}"
            )
            return count

        except Exception as e:
            logger.error(f"Error syncing PortfolioStats for empresa {empresa_id}: {e}")
            self.db.rollback()
            raise

    # ============================================
    # Delinquency Synchronization
    # ============================================

    def sync_delinquency(
        self,
        empresa_id: int,
        ref_date: date,
        parcelas_data: Optional[Dict[str, List[Dict[str, Any]]]] = None,
        dev: Optional[Any] = None,  # Optional pre-loaded Development to avoid extra query
    ) -> int:
        """
        Synchronize Delinquency (inadimplencia) for an empresa.

        Args:
            empresa_id: Empresa ID
            ref_date: Reference date for calculation
            parcelas_data: Optional pre-fetched parcelas data (to avoid duplicate API calls)
            dev: Optional pre-loaded Development object (optimization)

        Returns:
            1 if record created, 0 otherwise
        """
        from starke.infrastructure.database.models import Delinquency, Development

        logger.info(f"Syncing Delinquency for empresa {empresa_id} ({ref_date})")

        try:
            # Use pre-loaded Development or fetch from DB
            if dev is None:
                dev = self.db.query(Development).filter(
                    Development.external_id == empresa_id,
                    Development.origem == "uau"
                ).first()

            if not dev:
                logger.warning(f"Empresa external_id={empresa_id} not found in database")
                return 0

            empreendimento_internal_id = dev.id  # Internal ID for DB relations

            # Get all parcelas (a receber + recebidas) if not pre-fetched
            if parcelas_data is None:
                parcelas_data = self.api_client.get_all_parcelas_empresa(
                    empresa=empresa_id,
                    data_inicio="2000-01-01",
                    data_fim=ref_date.isoformat(),
                )

            parcelas_a_receber = parcelas_data.get("a_receber", [])
            parcelas_recebidas = parcelas_data.get("recebidas", [])

            logger.info(
                f"Found {len(parcelas_a_receber)} parcelas a receber and "
                f"{len(parcelas_recebidas)} parcelas recebidas for delinquency calc"
            )

            # Transform to Delinquency (use internal ID)
            delinquency = self.transformer.transform_parcelas_to_delinquency(
                parcelas_a_receber, parcelas_recebidas, empreendimento_internal_id, dev.name, ref_date
            )

            # Clear existing record (use internal ID)
            ref_month = ref_date.strftime("%Y-%m")
            self.db.query(Delinquency).filter(
                Delinquency.empreendimento_id == empreendimento_internal_id,
                Delinquency.ref_month == ref_month,
                Delinquency.origem == "uau",
            ).delete()

            # Insert new record
            delinquency_record = Delinquency(**delinquency)
            self.db.add(delinquency_record)
            self.db.commit()

            logger.info(
                f"Saved Delinquency for empresa {empresa_id}: "
                f"Total={delinquency['total']:,.2f}"
            )
            return 1

        except Exception as e:
            logger.error(f"Error syncing Delinquency for empresa {empresa_id}: {e}")
            self.db.rollback()
            raise

    # ============================================
    # Full Synchronization
    # ============================================

    def sync_all(
        self,
        empresa_ids: Optional[List[int]] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        skip_recent_hours: int = 0,
    ) -> Dict[str, Any]:
        """
        Perform full synchronization for UAU data.

        Args:
            empresa_ids: Optional list of empresa IDs to sync (defaults to all)
            start_date: Start date for financial data
            end_date: End date for financial data
            skip_recent_hours: Skip empresas synced within X hours (0 = process all)

        Returns:
            Dict with sync statistics
        """
        from starke.infrastructure.database.models import Development

        logger.info("Starting full UAU synchronization")

        # Default dates
        if end_date is None:
            end_date = date.today()
        if start_date is None:
            # Default to 12 months ago
            start_date = date(end_date.year - 1, end_date.month, 1)

        # Format dates
        data_inicio = start_date.isoformat()
        data_fim = end_date.isoformat()

        # Format for desembolso endpoint (MM/YYYY)
        mes_inicial = start_date.strftime("%m/%Y")
        mes_final = end_date.strftime("%m/%Y")

        stats = {
            "empresas_synced": 0,
            "developments_skipped": 0,
            "contracts_synced": 0,
            "cash_out_records": 0,
            "cash_in_records": 0,
            "portfolio_stats_records": 0,
            "delinquency_records": 0,
            "errors": [],
        }

        try:
            # Step 1: Sync empresas
            logger.info("Step 1: Syncing empresas")
            stats["empresas_synced"] = self.sync_empresas()

            # Step 2: Get ACTIVE empresas to process
            # Only sync empresas that have been manually activated by the user
            query = self.db.query(Development).filter(
                Development.origem == "uau",
                Development.is_active == True,  # Only process active empresas
            )

            if empresa_ids:
                query = query.filter(Development.external_id.in_(empresa_ids))

            empresas = query.all()

            # Count inactive empresas
            total_uau = self.db.query(Development).filter(Development.origem == "uau").count()
            inactive_count = total_uau - len(empresas)
            stats["developments_skipped"] = inactive_count

            if not empresas:
                logger.warning(
                    "No active UAU empresas to sync. "
                    "Activate empresas via API (PATCH /developments/{id}/activate) first."
                )
                return stats

            logger.info(f"Processing {len(empresas)} active empresas ({inactive_count} inactive skipped)")

            # Checkpoint: skip empresas synced recently
            cutoff_time = utc_now() - timedelta(hours=skip_recent_hours) if skip_recent_hours > 0 else None

            # Step 3: Sync financial data for each empresa
            for empresa in empresas:
                try:
                    # CHECKPOINT: Skip if recently synced
                    if cutoff_time and empresa.last_financial_sync_at and empresa.last_financial_sync_at > cutoff_time:
                        hours_ago = (utc_now() - empresa.last_financial_sync_at).total_seconds() / 3600
                        logger.info(f"Skipping {empresa.name} - synced {hours_ago:.1f}h ago (within {skip_recent_hours}h)")
                        stats["developments_skipped"] += 1
                        continue

                    # Use external_id for API calls, pass empresa (Development) to avoid extra queries
                    external_id = empresa.external_id
                    logger.info(f"Processing empresa: {empresa.name} (external_id: {external_id})")

                    # === COMMIT before long API call to release DB connection ===
                    # This prevents connection timeout during the slow API fetch
                    self.db.commit()

                    # === SINGLE API CALL: Fetch vendas ONCE for all operations ===
                    # ExportarVendasXml returns complete vendas with embedded parcelas
                    # Used for: Contracts + CashIn + Delinquency
                    vendas = self.api_client.exportar_vendas_por_periodo(
                        empresa=external_id,
                        data_inicio=data_inicio,
                        data_fim=data_fim,
                    )
                    logger.info(f"Fetched {len(vendas)} vendas via ExportarVendas (single call for all)")

                    # === Refresh DB connection after long API call ===
                    # pool_pre_ping will reconnect if connection died during API fetch
                    from sqlalchemy import text
                    self.db.execute(text("SELECT 1"))

                    # Sync Vendas (Contracts) - reuse fetched vendas
                    contracts_count = self._sync_vendas_from_data(
                        vendas, empresa
                    )
                    stats["contracts_synced"] += contracts_count

                    # Sync CashOut (separate endpoint - desembolso)
                    cash_out_count = self.sync_cash_out(
                        external_id, mes_inicial, mes_final, dev=empresa
                    )
                    stats["cash_out_records"] += cash_out_count

                    # === Sync CashIn + Delinquency from same vendas data ===
                    cash_in_count, delinquency_count = self._sync_cash_in_and_delinquency_from_data(
                        vendas, empresa, data_inicio, data_fim, end_date
                    )
                    stats["cash_in_records"] += cash_in_count
                    stats["delinquency_records"] += delinquency_count

                    # Extract vendas with open parcelas (for VP optimization)
                    # VP still needs ConsultarParcelasDaVenda for dynamic calculation
                    vendas_com_parcelas_a_receber = set()
                    for venda in vendas:
                        if venda.get("StatusVenda") == "1":  # Skip cancelled
                            continue
                        parcelas_data = venda.get("Parcelas", {})
                        parcelas = parcelas_data.get("Parcela", [])
                        if isinstance(parcelas, dict):
                            parcelas = [parcelas]
                        # Check if venda has any open parcelas
                        has_open = any(p.get("ParcelaRecebida") == "0" for p in parcelas)
                        if has_open:
                            venda_key = (
                                external_id,
                                venda.get("Obra"),
                                self.transformer._safe_int(venda.get("Numero")),
                            )
                            if all(venda_key):
                                vendas_com_parcelas_a_receber.add(venda_key)

                    if vendas_com_parcelas_a_receber:
                        logger.info(f"Found {len(vendas_com_parcelas_a_receber)} vendas with open parcelas (for VP optimization)")

                    # Sync PortfolioStats for each month in the period
                    # VP is calculated once (with current values) and saved for all months
                    months_to_process = list(self._get_months_between_dates(data_inicio, data_fim))
                    logger.info(f"Syncing PortfolioStats for {len(months_to_process)} months")

                    try:
                        portfolio_count = self.sync_portfolio_stats_for_months(
                            external_id,
                            months_to_process,
                            dev=empresa,
                            vendas_com_parcelas_a_receber=vendas_com_parcelas_a_receber if vendas_com_parcelas_a_receber else None
                        )
                        stats["portfolio_stats_records"] += portfolio_count
                    except Exception as e:
                        logger.warning(f"Error syncing PortfolioStats: {e}")

                    # Update last_financial_sync_at after successful financial sync
                    empresa.last_financial_sync_at = utc_now()
                    self.db.commit()
                    logger.info(f"Updated last_financial_sync_at for empresa {empresa.name}")

                except Exception as e:
                    error_msg = f"Error syncing empresa {empresa.name}: {e}"
                    logger.error(error_msg)
                    stats["errors"].append(error_msg)
                    continue

            logger.info("UAU synchronization completed")
            logger.info(f"Statistics: {stats}")

            return stats

        except Exception as e:
            logger.error(f"Fatal error during UAU synchronization: {e}")
            raise

    # ============================================
    # Helper Methods
    # ============================================

    def _sync_vendas_from_data(
        self,
        vendas: List[Dict[str, Any]],
        dev: Any,
    ) -> int:
        """
        Sync contracts from pre-fetched vendas data.

        Args:
            vendas: List of vendas from ExportarVendasXml
            dev: Development object

        Returns:
            Number of contracts synchronized
        """
        from datetime import datetime
        from decimal import Decimal
        from starke.infrastructure.database.models import Contract

        if not vendas:
            return 0

        empreendimento_internal_id = dev.id

        # Load existing contracts for this empresa
        existing_contracts = (
            self.db.query(Contract)
            .filter(
                Contract.empreendimento_id == empreendimento_internal_id,
                Contract.origem == "uau",
            )
            .all()
        )

        # Build lookup by (obra, cod_contrato)
        contracts_by_key = {
            (c.obra, c.cod_contrato): c for c in existing_contracts
        }

        # === Fetch IPCA data ONCE for all contracts ===
        ipca_data = {}
        try:
            from starke.domain.services.ipca_service import IPCAService

            # Find earliest signing date among active contracts to optimize IPCA fetch
            active_contracts_dates = []
            for venda in vendas:
                status_code = str(venda.get("StatusVenda", "0"))
                # Active statuses: 0=Normal, 4=Em acerto
                if status_code in ("0", "4"):
                    data_venda_str = venda.get("DataDaVenda")
                    if data_venda_str:
                        try:
                            data_venda = datetime.strptime(data_venda_str, "%Y-%m-%d").date()
                            active_contracts_dates.append(data_venda)
                        except Exception:
                            continue

            if active_contracts_dates:
                earliest_date = min(active_contracts_dates)
                ipca_service = IPCAService()
                ipca_data = ipca_service.fetch_ipca_data(earliest_date, date.today())
                logger.info(f"Fetched IPCA data from {earliest_date} to today ({len(ipca_data)} months)")
            else:
                logger.info("No active contracts with signing dates, skipping IPCA fetch")

        except Exception as e:
            logger.error(f"Failed to fetch IPCA data: {e}")

        count = 0
        for venda in vendas:
            try:
                contract_data = self.transformer.transform_venda_to_contract(
                    venda, empreendimento_internal_id
                )

                if not contract_data:
                    continue

                obra = contract_data["obra"]
                cod_contrato = contract_data["cod_contrato"]
                key = (obra, cod_contrato)

                # === Calculate IPCA-adjusted value for ACTIVE contracts ===
                valor_atualizado_ipca = None
                status = contract_data.get("status")
                data_assinatura = contract_data.get("data_assinatura")
                valor_contrato = contract_data.get("valor_contrato")

                # Active statuses: Normal, Em acerto
                is_active = status in ("Normal", "Em acerto")

                if is_active and ipca_data and data_assinatura and valor_contrato:
                    try:
                        # Calculate first month to apply IPCA (month AFTER signing)
                        year = data_assinatura.year
                        month = data_assinatura.month + 1
                        if month > 12:
                            month = 1
                            year += 1
                        first_correction_month = date(year, month, 1)

                        # Calculate accumulated IPCA from month after signing
                        accumulated = Decimal("1")
                        for month_key in sorted(ipca_data.keys()):
                            # Parse month_key (YYYY-MM) to compare with contract date
                            month_date = datetime.strptime(month_key + "-01", "%Y-%m-%d").date()

                            # Only accumulate IPCA from month AFTER contract signing
                            if month_date >= first_correction_month:
                                ipca_monthly = ipca_data[month_key]
                                accumulated *= (Decimal("1") + ipca_monthly / Decimal("100"))

                        # Calculate adjusted value
                        accumulated_percentage = (accumulated - Decimal("1")) * Decimal("100")
                        valor_atualizado_ipca = Decimal(str(valor_contrato)) * (Decimal("1") + accumulated_percentage / Decimal("100"))

                        logger.debug(
                            f"Calculated IPCA for contract {obra}/{cod_contrato}: "
                            f"R$ {float(valor_contrato):,.2f} → R$ {float(valor_atualizado_ipca):,.2f} "
                            f"({float(accumulated_percentage):.2f}% accumulated)"
                        )
                    except Exception as e:
                        logger.error(f"Failed to calculate IPCA for contract {obra}/{cod_contrato}: {e}")

                existing = contracts_by_key.get(key)

                if existing:
                    existing.status = contract_data["status"]
                    existing.valor_contrato = contract_data["valor_contrato"]
                    existing.valor_atualizado_ipca = valor_atualizado_ipca
                    existing.data_assinatura = contract_data["data_assinatura"]
                    existing.cliente_cpf = contract_data["cliente_cpf"]
                    existing.cliente_codigo = contract_data["cliente_codigo"]
                    existing.last_synced_at = contract_data["last_synced_at"]
                else:
                    new_contract = Contract(
                        cod_contrato=cod_contrato,
                        empreendimento_id=empreendimento_internal_id,
                        obra=obra,
                        origem="uau",
                        status=contract_data["status"],
                        valor_contrato=contract_data["valor_contrato"],
                        valor_atualizado_ipca=valor_atualizado_ipca,
                        data_assinatura=contract_data["data_assinatura"],
                        cliente_cpf=contract_data["cliente_cpf"],
                        cliente_codigo=contract_data["cliente_codigo"],
                        last_synced_at=contract_data["last_synced_at"],
                    )
                    self.db.add(new_contract)
                    contracts_by_key[key] = new_contract

                count += 1

            except Exception as e:
                logger.error(f"Error processing venda {venda.get('Numero')}: {e}")
                continue

        self.db.commit()
        logger.info(f"Synchronized {count} contracts from pre-fetched data")
        return count

    def _sync_cash_in_and_delinquency_from_data(
        self,
        vendas: List[Dict[str, Any]],
        dev: Any,
        data_inicio: str,
        data_fim: str,
        ref_date: date,
    ) -> Tuple[int, int]:
        """
        Sync CashIn and Delinquency from pre-fetched vendas data.

        Args:
            vendas: List of vendas from ExportarVendasXml
            dev: Development object
            data_inicio: Start date (YYYY-MM-DD)
            data_fim: End date (YYYY-MM-DD)
            ref_date: Reference date for delinquency

        Returns:
            Tuple of (cash_in_count, delinquency_count)
        """
        from starke.infrastructure.database.models import CashIn, Delinquency

        if not vendas:
            return 0, 0

        empresa_nome = dev.name
        empreendimento_internal_id = dev.id

        months_in_period = set(self._get_months_between_dates(data_inicio, data_fim))

        # === Process CashIn ===
        all_cash_in = []
        for venda in vendas:
            if venda.get("StatusVenda") == "1":
                continue

            obra = venda.get("Obra", "")
            num_venda = self.transformer._safe_int(venda.get("Numero")) or 0

            parcelas_data = venda.get("Parcelas", {})
            parcelas = parcelas_data.get("Parcela", [])

            if isinstance(parcelas, dict):
                parcelas = [parcelas]

            for parcela in parcelas:
                records = self.transformer.transform_parcela_export_to_cash_in(
                    parcela, empreendimento_internal_id, empresa_nome, obra, num_venda
                )
                for record in records:
                    if record.get("ref_month") in months_in_period:
                        all_cash_in.append(record)

        aggregated_cash_in = self.transformer.aggregate_cash_in(all_cash_in)

        # === DB Operations ===
        from sqlalchemy import text
        from dateutil.relativedelta import relativedelta

        try:
            self.db.execute(text("SELECT 1"))
        except Exception:
            self.db.rollback()

        # Clear and insert CashIn
        cash_in_count = 0
        if months_in_period:
            self.db.query(CashIn).filter(
                CashIn.empreendimento_id == empreendimento_internal_id,
                CashIn.ref_month.in_(list(months_in_period)),
                CashIn.origem == "uau",
            ).delete(synchronize_session=False)

            for record_data in aggregated_cash_in.values():
                cash_in = CashIn(**record_data)
                self.db.add(cash_in)
                cash_in_count += 1

        # === Process Delinquency for EACH month in period (same as Mega) ===
        delinquency_count = 0
        for ref_month_str in sorted(months_in_period):
            try:
                year, month = map(int, ref_month_str.split("-"))
                month_start = date(year, month, 1)
                last_day_of_month = month_start + relativedelta(months=1) - relativedelta(days=1)

                # For future months, cap at today
                month_ref_date = min(last_day_of_month, date.today())

                delinquency = self.transformer.transform_parcelas_export_to_delinquency(
                    vendas, empreendimento_internal_id, empresa_nome, month_ref_date
                )

                # Override ref_month to use YYYY-MM format (transformer now returns YYYY-MM)
                delinquency["ref_month"] = ref_month_str

                # Clear existing and insert new
                self.db.query(Delinquency).filter(
                    Delinquency.empreendimento_id == empreendimento_internal_id,
                    Delinquency.ref_month == ref_month_str,
                    Delinquency.origem == "uau",
                ).delete()

                delinquency_record = Delinquency(**delinquency)
                self.db.add(delinquency_record)
                delinquency_count += 1

                if delinquency["total"] > 0:
                    logger.info(
                        f"Delinquency {ref_month_str}: total={delinquency['total']:,.2f} "
                        f"({delinquency['details']['parcelas_inadimplentes']} inadimplentes)"
                    )
            except Exception as e:
                logger.error(f"Error calculating Delinquency for {empresa_nome} - {ref_month_str}: {e}")

        self.db.commit()

        logger.info(
            f"From pre-fetched data: {cash_in_count} CashIn, "
            f"{delinquency_count} Delinquency records"
        )

        return cash_in_count, delinquency_count

    def _get_months_in_range(self, mes_inicial: str, mes_final: str) -> List[str]:
        """
        Get list of months between mes_inicial and mes_final.

        Args:
            mes_inicial: Start month in "MM/YYYY" format
            mes_final: End month in "MM/YYYY" format

        Returns:
            List of months in "YYYY-MM" format
        """
        from dateutil.relativedelta import relativedelta

        # Parse MM/YYYY
        start_month, start_year = map(int, mes_inicial.split("/"))
        end_month, end_year = map(int, mes_final.split("/"))

        months = []
        current = date(start_year, start_month, 1)
        end = date(end_year, end_month, 1)

        while current <= end:
            months.append(current.strftime("%Y-%m"))
            current += relativedelta(months=1)

        return months

    def _get_months_between_dates(self, data_inicio: str, data_fim: str) -> List[str]:
        """
        Get list of months between two dates.

        Args:
            data_inicio: Start date in "YYYY-MM-DD" format
            data_fim: End date in "YYYY-MM-DD" format

        Returns:
            List of months in "YYYY-MM" format
        """
        from dateutil.relativedelta import relativedelta

        start = datetime.strptime(data_inicio, "%Y-%m-%d").date().replace(day=1)
        end = datetime.strptime(data_fim, "%Y-%m-%d").date().replace(day=1)

        months = []
        current = start

        while current <= end:
            months.append(current.strftime("%Y-%m"))
            current += relativedelta(months=1)

        return months


# Import timedelta for use in sync methods
from datetime import timedelta
