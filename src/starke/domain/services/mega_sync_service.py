"""Mega API synchronization service - orchestrates data import from Mega to Starke."""

import gc
import logging
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Optional

from sqlalchemy import tuple_
from sqlalchemy.orm import Session

from starke.core.config import get_settings
from starke.core.date_helpers import utc_now
from starke.core.config_loader import get_mega_config
from starke.domain.services.cash_flow_service import CashFlowService
from starke.domain.services.mega_transformer import MegaDataTransformer
from starke.domain.services.portfolio_calculator import PortfolioCalculator
from starke.infrastructure.database.models import Development
from starke.infrastructure.external_apis.mega_api_client import MegaAPIClient

logger = logging.getLogger(__name__)


class MegaSyncService:
    """Service to synchronize data from Mega API to Starke database."""

    def __init__(self, db: Session, api_client: Optional[MegaAPIClient] = None):
        """
        Initialize sync service.

        Args:
            db: Database session
            api_client: Optional Mega API client (creates new one if not provided)
        """
        self.db = db
        self.api_client = api_client
        self.transformer = MegaDataTransformer()
        self.calculator = PortfolioCalculator()
        self.cash_flow_service = CashFlowService(db)
        self.config = get_mega_config()

        self._client_owned = api_client is None

    def __enter__(self):
        """Context manager entry."""
        if self._client_owned:
            self.api_client = MegaAPIClient()
            self.api_client.__enter__()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        if self._client_owned and self.api_client:
            self.api_client.__exit__(exc_type, exc_val, exc_tb)

    def _safe_commit(self, operation_name: str = "commit") -> bool:
        """
        Commit with retry on connection errors.

        Args:
            operation_name: Name for logging

        Returns:
            True if commit succeeded
        """
        from starke.infrastructure.database.base import execute_with_retry

        def do_commit():
            self.db.commit()
            return True

        try:
            return execute_with_retry(
                self.db,
                do_commit,
                max_retries=3,
                retry_delay=2.0,
                operation_name=operation_name
            )
        except Exception as e:
            logger.error(f"Commit failed after retries: {e}")
            raise

    # ============================================
    # Parallel API Fetching
    # ============================================

    def fetch_parcelas_parallel(
        self, contract_ids: List[int], max_workers: Optional[int] = None
    ) -> Dict[int, List]:
        """
        Fetch parcelas for multiple contracts in parallel using ThreadPoolExecutor.

        OPTIMIZATION: Test showed 50 contracts, 29,674 parcelas:
        - 8 workers: 12.11s
        - 16 workers: 8.45s
        - No rate limiting observed

        Args:
            contract_ids: List of contract IDs to fetch parcelas for
            max_workers: Number of parallel workers (uses MEGA_MAX_WORKERS from .env, default: 4)

        Returns:
            Dict mapping contract_id -> list of parcelas
        """
        if not contract_ids:
            return {}

        # Use config if max_workers not specified
        if max_workers is None:
            settings = get_settings()
            max_workers = settings.mega_max_workers

        results = {}
        errors = []

        def fetch_one(cid: int):
            """Fetch parcelas for a single contract."""
            try:
                parcelas = self.api_client.get_parcelas_by_contract_id(cid)
                return cid, parcelas, None
            except Exception as e:
                return cid, [], str(e)

        logger.info(f"Fetching parcelas for {len(contract_ids)} contracts using {max_workers} parallel workers...")
        start_time = time.time()

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = [executor.submit(fetch_one, cid) for cid in contract_ids]

            for future in as_completed(futures):
                cid, parcelas, error = future.result()
                if error:
                    errors.append(f"Contract {cid}: {error}")
                else:
                    results[cid] = parcelas

        elapsed = time.time() - start_time
        total_parcelas = sum(len(p) for p in results.values())

        logger.info(
            f"✅ Fetched {total_parcelas} parcelas from {len(results)} contracts in {elapsed:.2f}s "
            f"({total_parcelas / elapsed:.0f} parcelas/sec)"
        )

        if errors:
            logger.warning(f"Failed to fetch parcelas for {len(errors)} contracts")
            for err in errors[:5]:  # Log first 5 errors
                logger.warning(f"  - {err}")

        return results

    # ============================================
    # Development Synchronization
    # ============================================

    def sync_developments(self, filial: Optional[int] = None) -> int:
        """
        Synchronize empreendimentos (developments) and filiais from Mega API.

        OPTIMIZED: Loads all existing records upfront to avoid N+1 queries.

        This method:
        1. Extracts unique filiais from empreendimentos data
        2. Creates/updates filiais in database
        3. Creates/updates developments with filial_id FK

        Args:
            filial: Optional filial filter

        Returns:
            Number of developments synchronized
        """
        from starke.infrastructure.database.models import Filial

        logger.info("Starting development and filial synchronization (OPTIMIZED)")

        try:
            # Fetch empreendimentos from Mega API
            empreendimentos = self.api_client.get_empreendimentos(
                filial=filial, expand="projeto,centroCusto,filial"
            )

            logger.info(f"Found {len(empreendimentos)} developments in Mega API")

            # ============================================
            # OPTIMIZATION: Load all existing records upfront (2 queries total)
            # With retry for connection resilience
            # ============================================
            from starke.infrastructure.database.base import execute_with_retry

            logger.info("Loading existing filiais and developments from database...")

            # Load all Mega filiais with retry
            existing_filiais = execute_with_retry(
                self.db,
                lambda: self.db.query(Filial).filter(Filial.origem == "mega").all(),
                max_retries=3,
                operation_name="load filiais"
            )
            filial_by_external_id = {f.external_id: f for f in existing_filiais}
            logger.info(f"Loaded {len(existing_filiais)} existing filiais")

            # Load all Mega developments with retry
            existing_developments = execute_with_retry(
                self.db,
                lambda: self.db.query(Development).filter(Development.origem == "mega").all(),
                max_retries=3,
                operation_name="load developments"
            )
            dev_by_external_id = {d.external_id: d for d in existing_developments}
            logger.info(f"Loaded {len(existing_developments)} existing developments")

            # ============================================
            # Step 1: Extract and sync unique filiais
            # ============================================
            filiais_data = {}
            for emp_data in empreendimentos:
                filial_codigo = emp_data.get("codigoFilial")
                if filial_codigo and filial_codigo not in filiais_data:
                    filiais_data[filial_codigo] = {
                        "id": int(filial_codigo),
                        "nome": emp_data.get("nomeFilial", f"Filial {filial_codigo}"),
                        "fantasia": emp_data.get("fantasiaFilial"),
                        "cnpj": emp_data.get("cnpjFilial"),
                    }

            logger.info(f"Found {len(filiais_data)} unique filiais in API data")

            # Upsert filiais using in-memory lookup (no queries in loop)
            filiais_created = 0
            filiais_updated = 0
            for external_filial_id, filial_info in filiais_data.items():
                existing_filial = filial_by_external_id.get(external_filial_id)

                if existing_filial:
                    # Update existing
                    existing_filial.nome = filial_info["nome"]
                    existing_filial.fantasia = filial_info["fantasia"]
                    existing_filial.cnpj = filial_info["cnpj"]
                    existing_filial.atualizado_em = utc_now()
                    filiais_updated += 1
                else:
                    # Create new with external_id (inactive by default, will be activated if has active developments)
                    new_filial = Filial(
                        external_id=external_filial_id,
                        nome=filial_info["nome"],
                        fantasia=filial_info["fantasia"],
                        cnpj=filial_info["cnpj"],
                        origem="mega",
                        is_active=False,
                        criado_em=utc_now(),
                    )
                    self.db.add(new_filial)
                    # Add to lookup for use in development sync
                    filial_by_external_id[external_filial_id] = new_filial
                    filiais_created += 1

            # Commit filiais first to get IDs for new filiais
            self.db.commit()

            # Refresh lookup to get IDs for newly created filiais
            if filiais_created > 0:
                existing_filiais = self.db.query(Filial).filter(Filial.origem == "mega").all()
                filial_by_external_id = {f.external_id: f for f in existing_filiais}

            logger.info(f"Filiais: {filiais_created} created, {filiais_updated} updated")

            # ============================================
            # Step 2: Sync developments using in-memory lookup
            # ============================================
            count = 0
            devs_created = 0
            devs_updated = 0

            for emp_data in empreendimentos:
                try:
                    # Transform to Starke format
                    transformed = self.transformer.transform_empreendimento(emp_data)

                    # Extract external IDs
                    external_dev_id = transformed.get("external_id")
                    external_filial_id = transformed.get("_filial_codigo")
                    centro_custo = transformed.get("_centro_custo")

                    # Get internal filial_id from in-memory lookup (no query!)
                    filial_internal_id = None
                    if external_filial_id:
                        filial_obj = filial_by_external_id.get(external_filial_id)
                        if filial_obj:
                            filial_internal_id = filial_obj.id

                    # Check if development exists using in-memory lookup (no query!)
                    existing = dev_by_external_id.get(external_dev_id)

                    if existing:
                        # Update existing
                        existing.name = transformed["name"]
                        existing.is_active = transformed["is_active"]
                        existing.filial_id = filial_internal_id
                        existing.centro_custo_id = centro_custo
                        existing.raw_data = transformed["raw_data"]
                        existing.last_synced_at = transformed["last_synced_at"]
                        existing.updated_at = utc_now()
                        devs_updated += 1
                    else:
                        # Create new with external_id
                        new_dev = Development(
                            external_id=external_dev_id,
                            name=transformed["name"],
                            is_active=transformed["is_active"],
                            filial_id=filial_internal_id,
                            centro_custo_id=centro_custo,
                            raw_data=transformed["raw_data"],
                            origem="mega",
                            last_synced_at=transformed["last_synced_at"],
                        )
                        self.db.add(new_dev)
                        devs_created += 1

                    count += 1

                except Exception as e:
                    logger.error(f"Error processing development {emp_data.get('codigo', 'UNKNOWN')}: {e}")
                    continue

            # Commit all development changes
            self.db.commit()

            logger.info(f"Developments: {devs_created} created, {devs_updated} updated")
            logger.info(f"✅ Successfully synchronized {len(filiais_data)} filiais and {count} developments (OPTIMIZED)")
            return count

        except Exception as e:
            logger.error(f"Error synchronizing developments: {e}")
            self.db.rollback()
            raise

    # ============================================
    # Cash In Synchronization
    # ============================================

    def sync_cash_in_for_development(
        self, development: Development, start_date: date, end_date: date,
        pre_fetched_contratos: List[Dict[str, Any]] = None
    ) -> dict:
        """
        Synchronize cash in (receivables) for a specific development.

        This includes:
        - Saving contracts to database
        - Ativos (contract installments)
        - Antecipações (if available)
        - Recuperações (if available)
        - Outras receitas (if available)

        Args:
            development: Development to sync
            start_date: Start date for sync
            end_date: End date for sync

        Returns:
            Dict with counts: {contracts_saved, cash_in_records}
        """
        from starke.infrastructure.database.models import CashIn, Contract

        logger.info(
            f"Syncing CashIn for {development.name} from {start_date} to {end_date}"
        )

        cash_in_count = 0
        contracts_saved = 0

        try:
            # Use the external_id (Mega's ID) for fetching contracts from API
            # API route: /api/Carteira/DadosContrato/IdEmpreendimento={external_id}
            mega_empreendimento_id = development.external_id

            # 1. Fetch contracts from Mega API (or use pre-fetched)
            if pre_fetched_contratos is not None:
                logger.debug(f"Using {len(pre_fetched_contratos)} pre-fetched contracts for {development.name}")
                contratos = pre_fetched_contratos
            else:
                logger.debug(f"Fetching contracts for development {development.name} (external_id: {mega_empreendimento_id})")
                contratos = self.api_client.get_contratos_by_development_id(mega_empreendimento_id)

            logger.info(f"Found {len(contratos)} contracts for {development.name}")

            # 2. Fetch IPCA data ONCE for all contracts
            ipca_data = {}
            try:
                from starke.domain.services.ipca_service import IPCAService
                from decimal import Decimal

                # Find earliest signing date among active contracts
                active_contracts_dates = []
                for contrato in contratos:
                    # Check both "status" and "status_contrato" fields
                    # API can return "Ativo" or "A" for active contracts
                    status = contrato.get("status_contrato") or contrato.get("status")
                    data_assinatura_str = contrato.get("data_assinatura")

                    # Check if contract is active
                    is_active = self.config.is_contrato_ativo(status) if status else False

                    if is_active and data_assinatura_str:
                        try:
                            data_assinatura = self.transformer._parse_date(data_assinatura_str)
                            if data_assinatura:
                                active_contracts_dates.append(data_assinatura)
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

            # 3. Save contracts to database
            # Delete existing contracts for this development first
            deleted = self.db.query(Contract).filter(
                Contract.empreendimento_id == development.id
            ).delete()
            logger.debug(f"Deleted {deleted} existing contracts for {development.name}")

            # Save new contracts
            for contrato in contratos:
                try:
                    # Transform contract data
                    contract_data = self.transformer.transform_contrato(
                        contrato, development.id, development.name
                    )

                    # Calculate IPCA-adjusted value for ACTIVE contracts only
                    valor_atualizado_ipca = None
                    status = contract_data.get("status")
                    data_assinatura = contract_data.get("data_assinatura")
                    valor_contrato = contract_data.get("valor_contrato")

                    # Check if contract is active (handles both "Ativo" and "A")
                    is_active = self.config.is_contrato_ativo(status) if status else False

                    if is_active and ipca_data and data_assinatura and valor_contrato:
                        try:
                            # Calculate first month to apply IPCA (month AFTER signing)
                            # E.g., if signed on 14/03/2025, first correction is 01/04/2025
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
                                f"Calculated IPCA for contract {contract_data.get('cod_contrato')}: "
                                f"R$ {float(valor_contrato):,.2f} → R$ {float(valor_atualizado_ipca):,.2f} "
                                f"({float(accumulated_percentage):.2f}% accumulated)"
                            )
                        except Exception as e:
                            logger.error(f"Failed to calculate IPCA for contract {contract_data.get('cod_contrato')}: {e}")

                    # Add valor_atualizado_ipca to contract data
                    contract_data["valor_atualizado_ipca"] = valor_atualizado_ipca

                    # Create Contract record
                    contract = Contract(**contract_data)
                    self.db.add(contract)
                    contracts_saved += 1

                except Exception as e:
                    logger.error(f"Error saving contract {contrato.get('cod_contrato')}: {e}")
                    continue

            # Commit contracts before processing parcelas
            self.db.commit()
            logger.info(f"Saved {contracts_saved} contracts for {development.name}")

            # 3. Clear existing CashIn records for the period
            # ref_month is stored as 'YYYY-MM', so we need to convert dates to this format
            # for proper comparison. Get all unique months in the date range.
            from dateutil.relativedelta import relativedelta

            months_to_delete = set()
            current = start_date.replace(day=1)  # Start from first day of start month
            end = end_date.replace(day=1)  # Compare up to first day of end month

            while current <= end:
                months_to_delete.add(current.strftime('%Y-%m'))
                current += relativedelta(months=1)

            # Delete records for all months in the range (ALL categories) - ONLY MEGA
            if months_to_delete:
                self.db.query(CashIn).filter(
                    CashIn.empreendimento_id == development.id,
                    CashIn.ref_month.in_(list(months_to_delete)),
                    CashIn.origem == "mega"  # IMPORTANT: Only delete Mega records, not UAU
                ).delete(synchronize_session=False)

            # 4. Fetch all parcelas from all contracts IN PARALLEL (for reuse in calculations)
            # OPTIMIZATION: Use parallel fetching to reduce API call time significantly
            contract_ids = [
                int(c.get("cod_contrato"))
                for c in contratos
                if c.get("cod_contrato")
            ]

            if contract_ids:
                # Fetch parcelas in parallel (uses MEGA_MAX_WORKERS from .env)
                parcelas_by_contract = self.fetch_parcelas_parallel(contract_ids)
                # Flatten the results
                todas_parcelas = [p for ps in parcelas_by_contract.values() for p in ps]
            else:
                todas_parcelas = []

            logger.info(f"Collected {len(todas_parcelas)} parcelas for {development.name}")

            # 5. Process CashIn month by month using CashFlowService
            # This properly classifies parcelas into categories (ativos, recuperacoes, antecipacoes, outras)

            # OPTIMIZATION: Skip month-by-month processing if no parcelas
            if not todas_parcelas:
                logger.info(f"No parcelas to process for {development.name}, skipping CashIn calculation")
                return {
                    "contracts_saved": contracts_saved,
                    "cash_in_records": 0,
                    "contratos": contratos,
                    "parcelas": [],
                }

            from dateutil.relativedelta import relativedelta

            current = start_date.replace(day=1)
            while current <= end_date:
                # Calculate last day of month
                if current.month == 12:
                    next_month = current.replace(year=current.year + 1, month=1)
                else:
                    next_month = current.replace(month=current.month + 1)

                last_day = next_month - timedelta(days=1)
                ref_date = min(last_day, end_date)

                logger.debug(f"Processing CashIn for {current.strftime('%Y-%m')} (ref_date: {ref_date})")

                # Use CashFlowService to calculate with proper categorization
                cash_in_list = self.cash_flow_service.calculate_cash_in_from_parcelas(
                    parcelas=todas_parcelas,
                    empreendimento_id=development.id,
                    empreendimento_nome=development.name,
                    ref_date=ref_date,
                )

                # Save each category record
                for cash_in_data in cash_in_list:
                    # Convert to dict for CashIn model
                    cash_in = CashIn(
                        empreendimento_id=cash_in_data.empreendimento_id,
                        empreendimento_nome=cash_in_data.empreendimento_nome,
                        ref_month=ref_date.strftime('%Y-%m'),
                        category=cash_in_data.category.value,
                        forecast=float(cash_in_data.forecast),
                        actual=float(cash_in_data.actual),
                    )
                    self.db.add(cash_in)
                    cash_in_count += 1

                # Commit after each month to avoid long transactions
                self._safe_commit(f"cash_in_{ref_date.strftime('%Y-%m')}")

                # Move to next month
                current = next_month

            logger.info(
                f"Synchronized {contracts_saved} contracts and {cash_in_count} CashIn records for {development.name}"
            )
            logger.info(f"Collected {len(todas_parcelas)} parcelas for reuse in portfolio calculations")

            return {
                "contracts_saved": contracts_saved,
                "cash_in_records": cash_in_count,
                "contratos": contratos,
                "parcelas": todas_parcelas,
            }

        except Exception as e:
            logger.error(f"Error syncing CashIn for {development.name}: {e}")
            self.db.rollback()
            raise

    # ============================================
    # Cash Out Synchronization
    # ============================================

    def sync_cash_out_bulk(
        self, start_date: date, end_date: date, development_ids: Optional[List[int]] = None
    ) -> int:
        """
        OPTIMIZED: Synchronize cash out (expenses) for all developments in one API call.

        This method:
        1. Fetches ALL FaturaPagar in one API call (no filial filter)
        2. Maps Agente.Codigo → cod_contrato → development_id (batch query)
        3. Processes forecast and actual values:
           - Forecast: ValorParcela
           - Actual: ValorParcela - SaldoAtual

        Args:
            start_date: Start date for sync
            end_date: End date for sync
            development_ids: Optional list of development IDs to process (for filtering)

        Returns:
            Total number of CashOut records created
        """
        from starke.infrastructure.database.models import CashOut, Contract
        from dateutil.relativedelta import relativedelta
        from decimal import Decimal

        logger.info(f"Syncing CashOut (bulk) from {start_date} to {end_date}")

        try:
            # Step 1: Fetch ALL faturas from API (single call)
            all_faturas = self.api_client.get_faturas_pagar(
                vencto_inicial=start_date.isoformat(),
                vencto_final=end_date.isoformat(),
                expand="classeFinanceira,centroCusto,fornecedor",
            )

            logger.info(f"Fetched {len(all_faturas)} faturas from Mega API")

            if not all_faturas:
                logger.info("No faturas found in period")
                return 0

            # Step 2: Extract all unique Agente.Codigo (contract codes)
            agente_codigos = set()
            for fatura in all_faturas:
                agente = fatura.get("Agente", {})
                if isinstance(agente, dict):
                    codigo = agente.get("Codigo")
                    if codigo:
                        agente_codigos.add(int(codigo))

            logger.info(f"Found {len(agente_codigos)} unique contract codes in faturas")

            if not agente_codigos:
                logger.warning("No valid Agente.Codigo found in faturas")
                return 0

            # Step 3: Batch query contracts from database
            contracts_query = self.db.query(Contract).filter(
                Contract.cod_contrato.in_(list(agente_codigos))
            )

            # Filter by development_ids if provided
            if development_ids:
                contracts_query = contracts_query.filter(
                    Contract.empreendimento_id.in_(development_ids)
                )

            contracts = contracts_query.all()

            logger.info(f"Found {len(contracts)} contracts in database")

            # Step 4: Create mapping cod_contrato → (development_id, development_name)
            contract_map = {}
            for contract in contracts:
                contract_map[contract.cod_contrato] = {
                    "development_id": contract.empreendimento_id,
                    "development_name": None  # Will fetch later if needed
                }

            # Fetch development names (batch query) - only Mega developments
            dev_ids = list(set(c["development_id"] for c in contract_map.values()))
            from starke.infrastructure.database.models import Development
            developments = self.db.query(Development).filter(
                Development.id.in_(dev_ids),
                Development.origem == "mega"
            ).all()

            dev_name_map = {dev.id: dev.name for dev in developments}

            # Update contract_map with development names
            for cod_contrato, info in contract_map.items():
                info["development_name"] = dev_name_map.get(info["development_id"], f"Dev_{info['development_id']}")

            # Step 5: Clear existing CashOut records for the period
            months_to_delete = set()
            current = start_date.replace(day=1)
            end = end_date.replace(day=1)

            while current <= end:
                months_to_delete.add(current.strftime('%Y-%m'))
                current += relativedelta(months=1)

            if months_to_delete:
                delete_query = self.db.query(CashOut).filter(
                    CashOut.mes_referencia.in_(list(months_to_delete)),
                    CashOut.origem == "mega"  # IMPORTANT: Only delete Mega records, not UAU
                )
                if development_ids:
                    delete_query = delete_query.filter(
                        CashOut.filial_id.in_(development_ids)
                    )
                deleted_count = delete_query.delete(synchronize_session=False)
                logger.info(f"Deleted {deleted_count} existing Mega CashOut records")

            # Step 6: Process faturas and create CashOut records
            cash_out_records = []
            skipped_count = 0

            for fatura in all_faturas:
                try:
                    # Extract Agente.Codigo (contract code)
                    agente = fatura.get("Agente", {})
                    if not isinstance(agente, dict):
                        continue

                    agente_codigo = agente.get("Codigo")
                    if not agente_codigo:
                        continue

                    agente_codigo = int(agente_codigo)

                    # Check if contract exists in our mapping
                    if agente_codigo not in contract_map:
                        skipped_count += 1
                        if skipped_count <= 10:  # Log only first 10
                            logger.debug(f"Contract {agente_codigo} not found in database, skipping")
                        continue

                    contract_info = contract_map[agente_codigo]
                    development_id = contract_info["development_id"]
                    development_name = contract_info["development_name"]

                    # Extract values
                    valor_parcela = self.transformer._parse_decimal(fatura.get("ValorParcela", 0))
                    saldo_atual = self.transformer._parse_decimal(fatura.get("SaldoAtual", 0))

                    # Calculate forecast and actual
                    forecast = valor_parcela
                    actual = valor_parcela - saldo_atual if saldo_atual < valor_parcela else Decimal("0")

                    # Extract date
                    dt_vencimento_str = fatura.get("DataVencimento")
                    dt_vencimento = self.transformer._parse_date(dt_vencimento_str)

                    if not dt_vencimento:
                        logger.warning(f"Invalid DataVencimento for fatura: {dt_vencimento_str}")
                        continue

                    ref_month = dt_vencimento.strftime('%Y-%m')

                    # Use TipoDocumento directly as category
                    tipo_documento = fatura.get("TipoDocumento", "OUTROS")
                    category = tipo_documento if tipo_documento else "OUTROS"

                    # Create CashOut record for forecast
                    if forecast > 0:
                        cash_out_records.append({
                            "empreendimento_id": development_id,
                            "empreendimento_nome": development_name,
                            "ref_month": ref_month,
                            "category": category,
                            "budget": float(forecast),
                            "actual": float(actual) if actual > 0 else 0.0,
                        })

                except Exception as e:
                    logger.error(f"Error processing fatura: {e}", exc_info=True)
                    continue

            if skipped_count > 10:
                logger.warning(f"Skipped {skipped_count} faturas (contracts not in database)")

            # Step 7: Aggregate records by (development_id, ref_month, category)
            aggregated = {}
            for record in cash_out_records:
                key = (
                    record["empreendimento_id"],
                    record["ref_month"],
                    record["category"]
                )

                if key not in aggregated:
                    aggregated[key] = record.copy()
                else:
                    # Sum budget and actual
                    aggregated[key]["budget"] += record["budget"]
                    aggregated[key]["actual"] += record["actual"]

            # Step 8: Insert aggregated records
            count = 0
            for record_data in aggregated.values():
                cash_out = CashOut(**record_data)
                self.db.add(cash_out)
                count += 1

            self.db.commit()

            logger.info(f"✅ Synchronized {count} CashOut records (bulk)")
            return count

        except Exception as e:
            logger.error(f"Error in bulk CashOut sync: {e}", exc_info=True)
            self.db.rollback()
            raise

    def sync_faturas_pagar(
        self,
        start_date: date,
        end_date: date,
        filial_ids: Optional[List[int]] = None
    ) -> int:
        """
        Synchronize faturas a pagar (invoices to pay) from Mega API.

        This method:
        1. Fetches faturas from API (/api/FinanceiroMovimentacao/FaturaPagar/Saldo)
        2. For each fatura, determines data_baixa based on business logic:
           - If fatura exists in DB with saldo > 0 and now saldo = 0 → data_baixa = today
           - If fatura doesn't exist in DB and saldo = 0 → data_baixa = data_vencimento
           - Otherwise → data_baixa = NULL
        3. Upserts faturas in database

        Args:
            start_date: Start date for sync (vencimento range)
            end_date: End date for sync (vencimento range)
            filial_ids: Optional list of filial IDs to filter

        Returns:
            Total number of faturas processed
        """
        from starke.infrastructure.database.models import FaturaPagar
        from datetime import datetime

        logger.info(f"Syncing FaturaPagar from {start_date} to {end_date}")

        try:
            total_count = 0

            # If filial_ids provided, fetch for each filial separately
            # Otherwise, fetch all faturas without filter
            # NOTE: filial_ids are INTERNAL IDs, but API expects external_id (codigoFilial)
            if filial_ids:
                from starke.infrastructure.database.models import Filial
                # Convert internal IDs to external_ids for Mega API
                filiais = self.db.query(Filial).filter(
                    Filial.id.in_(filial_ids),
                    Filial.origem == "mega"
                ).all()
                external_filial_ids = [f.external_id for f in filiais]
                logger.info(f"Converted {len(filial_ids)} internal filial IDs to {len(external_filial_ids)} external IDs")

                all_faturas = []
                for external_filial_id in external_filial_ids:
                    logger.info(f"Fetching faturas for filial external_id={external_filial_id}")
                    faturas = self.api_client.get_faturas_pagar(
                        vencto_inicial=start_date.isoformat(),
                        vencto_final=end_date.isoformat(),
                        filial=external_filial_id,
                        expand="classeFinanceira,centroCusto,fornecedor",
                    )
                    all_faturas.extend(faturas)
                    logger.info(f"Fetched {len(faturas)} faturas for filial external_id={external_filial_id}")
            else:
                all_faturas = self.api_client.get_faturas_pagar(
                    vencto_inicial=start_date.isoformat(),
                    vencto_final=end_date.isoformat(),
                    expand="classeFinanceira,centroCusto,fornecedor",
                )

            logger.info(f"Fetched {len(all_faturas)} total faturas from Mega API")

            if not all_faturas:
                logger.info("No faturas found in period")
                return 0

            # Step 1: Transform all faturas first
            logger.info("Transforming faturas...")
            transformed_faturas = []
            for fatura in all_faturas:
                try:
                    transformed = self.transformer.transform_fatura_pagar(fatura)
                    transformed_faturas.append(transformed)
                except ValueError as e:
                    logger.warning(f"Skipping invalid fatura: {e}")
                    continue
                except Exception as e:
                    logger.error(f"Error transforming fatura: {e}", exc_info=True)
                    continue

            logger.info(f"Transformed {len(transformed_faturas)} faturas")

            # Step 1.5: Deduplicate faturas by (origem, filial_id, numero_ap, numero_parcela)
            # API may return duplicates, and PostgreSQL won't allow multiple updates to same key in one command
            logger.info("Deduplicating faturas...")
            seen_keys = set()
            deduped_faturas = []
            duplicates_count = 0

            for fatura in transformed_faturas:
                key = (fatura["origem"], fatura["filial_id"], fatura["numero_ap"], fatura["numero_parcela"])
                if key not in seen_keys:
                    seen_keys.add(key)
                    deduped_faturas.append(fatura)
                else:
                    duplicates_count += 1

            if duplicates_count > 0:
                logger.warning(f"⚠️  Found and removed {duplicates_count} duplicate faturas from API response")

            transformed_faturas = deduped_faturas
            logger.info(f"After deduplication: {len(transformed_faturas)} unique faturas")

            # Step 2: Fetch existing faturas in batches to avoid giant IN queries
            logger.info("Fetching existing faturas from database...")
            origem_filial_ap_parcela_tuples = [(f["origem"], f["filial_id"], f["numero_ap"], f["numero_parcela"]) for f in transformed_faturas]

            # Create a lookup dict for existing faturas
            existing_lookup = {}

            # Process in batches of 500 tuples
            batch_size = 500
            total_batches = (len(origem_filial_ap_parcela_tuples) + batch_size - 1) // batch_size

            logger.info(f"Processing {len(origem_filial_ap_parcela_tuples)} tuples in {total_batches} batches of {batch_size}")

            for i in range(0, len(origem_filial_ap_parcela_tuples), batch_size):
                batch = origem_filial_ap_parcela_tuples[i:i + batch_size]
                batch_num = (i // batch_size) + 1
                logger.info(f"Fetching batch {batch_num}/{total_batches} ({len(batch)} tuples)...")

                # Query existing faturas by (origem, filial_id, numero_ap, numero_parcela) tuples
                existing_faturas = self.db.query(FaturaPagar).filter(
                    tuple_(FaturaPagar.origem, FaturaPagar.filial_id, FaturaPagar.numero_ap, FaturaPagar.numero_parcela).in_(batch)
                ).all()

                # Add to lookup dict
                for f in existing_faturas:
                    existing_lookup[(f.origem, f.filial_id, f.numero_ap, f.numero_parcela)] = f

                logger.info(f"Batch {batch_num}/{total_batches}: found {len(existing_faturas)} existing faturas")

            logger.info(f"Found {len(existing_lookup)} total existing faturas in database")

            # Step 3: Separate into updates and inserts
            to_update = []
            to_insert = []
            now = utc_now()

            for transformed in transformed_faturas:
                try:
                    origem = transformed["origem"]
                    filial_id = transformed["filial_id"]
                    numero_ap = transformed["numero_ap"]
                    numero_parcela = transformed["numero_parcela"]
                    saldo_atual = transformed["saldo_atual"]

                    existing = existing_lookup.get((origem, filial_id, numero_ap, numero_parcela))

                    # Determine data_baixa based on business logic
                    data_baixa = None

                    if existing:
                        # Fatura exists in DB
                        if existing.saldo_atual > 0 and saldo_atual == 0:
                            # Was unpaid, now paid → use today as payment date
                            data_baixa = date.today()
                        elif existing.data_baixa:
                            # Keep existing data_baixa if already set
                            data_baixa = existing.data_baixa
                    else:
                        # Fatura doesn't exist in DB
                        if saldo_atual == 0:
                            # Already paid → use vencimento as payment date
                            data_baixa = transformed["data_vencimento"]

                    # Update transformed data with calculated data_baixa
                    transformed["data_baixa"] = data_baixa
                    transformed["atualizado_em"] = now

                    if existing:
                        # Mark for update
                        to_update.append((existing, transformed))
                    else:
                        # Mark for insert
                        transformed["criado_em"] = now
                        to_insert.append(transformed)

                except Exception as e:
                    logger.error(f"Error processing fatura {transformed.get('numero_ap')}/{transformed.get('numero_parcela')}: {e}")
                    continue

            logger.info(f"Preparing to update {len(to_update)} faturas and insert {len(to_insert)} new faturas")

            # Step 4: Bulk update existing faturas using ON CONFLICT DO UPDATE
            if to_update:
                logger.info(f"Updating {len(to_update)} existing faturas using bulk update...")
                from sqlalchemy.dialects.postgresql import insert as pg_insert

                # Convert updates to upsert format (include id to preserve existing record)
                update_records = []
                for existing, transformed in to_update:
                    record = transformed.copy()
                    record['id'] = existing.id
                    update_records.append(record)

                # Process updates in batches of 1000
                batch_size = 1000
                updated_count = 0
                for i in range(0, len(update_records), batch_size):
                    batch = update_records[i:i + batch_size]
                    batch_num = (i // batch_size) + 1
                    total_batches = (len(update_records) + batch_size - 1) // batch_size

                    stmt = pg_insert(FaturaPagar).values(batch)
                    stmt = stmt.on_conflict_do_update(
                        index_elements=['origem', 'filial_id', 'numero_ap', 'numero_parcela'],
                        set_={
                            'valor_parcela': stmt.excluded.valor_parcela,
                            'saldo_atual': stmt.excluded.saldo_atual,
                            'data_baixa': stmt.excluded.data_baixa,
                            'dados_brutos': stmt.excluded.dados_brutos,
                            'atualizado_em': stmt.excluded.atualizado_em,
                        }
                    )
                    result = self.db.execute(stmt)
                    self._safe_commit(f"faturas_update_batch_{batch_num}")
                    updated_count += len(batch)
                    logger.debug(f"Updated batch {batch_num}/{total_batches}")

                logger.info(f"✅ Bulk updated {updated_count} faturas")
                total_count += updated_count

            # Step 5: Bulk insert new faturas using ON CONFLICT DO NOTHING
            if to_insert:
                logger.info(f"Inserting {len(to_insert)} new faturas using bulk insert...")
                from sqlalchemy.dialects.postgresql import insert as pg_insert

                # Process inserts in batches of 1000
                batch_size = 1000
                inserted_count = 0
                for i in range(0, len(to_insert), batch_size):
                    batch = to_insert[i:i + batch_size]
                    batch_num = (i // batch_size) + 1
                    total_batches = (len(to_insert) + batch_size - 1) // batch_size

                    stmt = pg_insert(FaturaPagar).values(batch)
                    stmt = stmt.on_conflict_do_nothing(
                        index_elements=['origem', 'filial_id', 'numero_ap', 'numero_parcela']
                    )
                    result = self.db.execute(stmt)
                    self._safe_commit(f"faturas_insert_batch_{batch_num}")
                    batch_inserted = result.rowcount if result.rowcount > 0 else 0
                    inserted_count += batch_inserted
                    logger.debug(f"Inserted batch {batch_num}/{total_batches}")

                logger.info(f"✅ Bulk inserted {inserted_count} new faturas (skipped {len(to_insert) - inserted_count} duplicates)")
                total_count += inserted_count

            logger.info(f"✅ Synchronized {total_count} FaturaPagar records")
            return total_count

        except Exception as e:
            logger.error(f"Error in FaturaPagar sync: {e}", exc_info=True)
            self.db.rollback()
            raise

    def aggregate_cash_out_from_faturas(
        self,
        ref_month: Optional[str] = None,
        filial_ids: Optional[List[int]] = None
    ) -> int:
        """
        Aggregate faturas_pagar into cash_out table grouped by (filial_id, ref_month, category).

        OPTIMIZED: Uses SQL aggregation instead of loading all records into memory.

        This method:
        1. Uses SQL GROUP BY to aggregate faturas directly in the database
        2. Calculates:
           - budget: sum of all faturas (paid + unpaid) by vencimento month
           - actual: sum of paid faturas (valor_parcela - saldo_atual) by payment month
        3. Upserts into cash_out table

        IMPORTANT: FaturaPagar.filial_id stores the external API ID (codigoFilial),
        but CashOut.filial_id needs to store the internal database ID (filiais.id).
        This method converts external to internal IDs before saving.

        Args:
            ref_month: Optional specific month to aggregate (YYYY-MM format)
                      If None, aggregates all months
            filial_ids: Optional list of filial IDs (INTERNAL) to filter

        Returns:
            Number of CashOut records created/updated
        """
        from starke.infrastructure.database.models import FaturaPagar, CashOut, Filial
        from sqlalchemy import func, extract, text
        from sqlalchemy.sql import expression
        from decimal import Decimal
        from collections import defaultdict

        logger.info(f"Aggregating CashOut from FaturaPagar (month={ref_month}) - OPTIMIZED SQL VERSION")

        # Build mapping: external_filial_id -> internal_filial_id for Mega filiais
        filiais = self.db.query(Filial).filter(Filial.origem == "mega").all()
        external_to_internal = {f.external_id: f.id for f in filiais}
        internal_to_external = {f.id: f.external_id for f in filiais}
        internal_to_name = {f.id: f.nome for f in filiais}
        logger.info(f"Built external->internal filial mapping with {len(external_to_internal)} entries")

        # Convert internal filial_ids to external_ids for filtering FaturaPagar
        # FaturaPagar.filial_id stores external_id (codigoFilial), not internal ID!
        external_filial_ids_filter = None
        if filial_ids:
            external_filial_ids_filter = [
                internal_to_external[fid] for fid in filial_ids
                if fid in internal_to_external
            ]
            logger.info(f"Converted {len(filial_ids)} internal filial IDs to {len(external_filial_ids_filter)} external IDs for filtering")

        try:
            # ============================================
            # BUDGET AGGREGATION (by vencimento month) - SQL
            # ============================================
            logger.info("Running budget aggregation query...")

            budget_query = self.db.query(
                FaturaPagar.filial_id,
                FaturaPagar.filial_nome,
                func.to_char(FaturaPagar.data_vencimento, 'YYYY-MM').label('ref_month'),
                FaturaPagar.tipo_documento,
                func.sum(FaturaPagar.valor_parcela).label('total_budget'),
                func.count(FaturaPagar.id).label('count')
            ).group_by(
                FaturaPagar.filial_id,
                FaturaPagar.filial_nome,
                func.to_char(FaturaPagar.data_vencimento, 'YYYY-MM'),
                FaturaPagar.tipo_documento
            )

            if external_filial_ids_filter:
                budget_query = budget_query.filter(FaturaPagar.filial_id.in_(external_filial_ids_filter))

            if ref_month:
                year, month = map(int, ref_month.split('-'))
                budget_query = budget_query.filter(
                    extract('year', FaturaPagar.data_vencimento) == year,
                    extract('month', FaturaPagar.data_vencimento) == month
                )

            budget_results = budget_query.all()
            logger.info(f"Budget aggregation returned {len(budget_results)} rows")

            # Build budget dict
            budget_agg = {}
            for row in budget_results:
                external_filial_id = row.filial_id
                internal_filial_id = external_to_internal.get(external_filial_id)
                if not internal_filial_id:
                    continue

                key = (internal_filial_id, row.ref_month, row.tipo_documento)
                budget_agg[key] = {
                    "amount": Decimal(str(row.total_budget)) if row.total_budget else Decimal("0"),
                    "filial_nome": row.filial_nome or internal_to_name.get(internal_filial_id, f"Filial {internal_filial_id}"),
                    "count": row.count or 0
                }

            # ============================================
            # ACTUAL AGGREGATION (valor_pago = valor_parcela - saldo_atual) - SQL
            # ============================================
            logger.info("Running actual aggregation query...")

            # For actual, we calculate valor_pago and use data_baixa month if available
            actual_query = self.db.query(
                FaturaPagar.filial_id,
                FaturaPagar.filial_nome,
                func.coalesce(
                    func.to_char(FaturaPagar.data_baixa, 'YYYY-MM'),
                    func.to_char(FaturaPagar.data_vencimento, 'YYYY-MM')
                ).label('ref_month'),
                FaturaPagar.tipo_documento,
                func.sum(FaturaPagar.valor_parcela - FaturaPagar.saldo_atual).label('total_actual'),
                func.count(FaturaPagar.id).label('count')
            ).filter(
                FaturaPagar.valor_parcela > FaturaPagar.saldo_atual  # Only records with payments
            ).group_by(
                FaturaPagar.filial_id,
                FaturaPagar.filial_nome,
                func.coalesce(
                    func.to_char(FaturaPagar.data_baixa, 'YYYY-MM'),
                    func.to_char(FaturaPagar.data_vencimento, 'YYYY-MM')
                ),
                FaturaPagar.tipo_documento
            )

            if external_filial_ids_filter:
                actual_query = actual_query.filter(FaturaPagar.filial_id.in_(external_filial_ids_filter))

            if ref_month:
                year, month = map(int, ref_month.split('-'))
                # Filter by either data_baixa month or data_vencimento month
                actual_query = actual_query.filter(
                    (
                        (FaturaPagar.data_baixa.isnot(None)) &
                        (extract('year', FaturaPagar.data_baixa) == year) &
                        (extract('month', FaturaPagar.data_baixa) == month)
                    ) | (
                        (FaturaPagar.data_baixa.is_(None)) &
                        (extract('year', FaturaPagar.data_vencimento) == year) &
                        (extract('month', FaturaPagar.data_vencimento) == month)
                    )
                )

            actual_results = actual_query.all()
            logger.info(f"Actual aggregation returned {len(actual_results)} rows")

            # Build actual dict
            actual_agg = {}
            for row in actual_results:
                external_filial_id = row.filial_id
                internal_filial_id = external_to_internal.get(external_filial_id)
                if not internal_filial_id:
                    continue

                key = (internal_filial_id, row.ref_month, row.tipo_documento)
                actual_agg[key] = {
                    "amount": Decimal(str(row.total_actual)) if row.total_actual else Decimal("0"),
                    "filial_nome": row.filial_nome or internal_to_name.get(internal_filial_id, f"Filial {internal_filial_id}"),
                    "count": row.count or 0
                }

            # ============================================
            # MERGE AND UPSERT (OPTIMIZED BULK VERSION)
            # ============================================
            all_keys = set(budget_agg.keys()) | set(actual_agg.keys())
            logger.info(f"Aggregated into {len(all_keys)} unique (filial, month, category) combinations")

            if not all_keys:
                logger.info("No data to aggregate")
                return 0

            # OPTIMIZATION: Fetch all existing records in a single query
            # Extract unique filial_ids and months for filtering
            unique_filial_ids = list(set(k[0] for k in all_keys))
            unique_months = list(set(k[1] for k in all_keys))

            logger.info(f"Fetching existing CashOut records for {len(unique_filial_ids)} filiais and {len(unique_months)} months...")

            existing_records = self.db.query(CashOut).filter(
                CashOut.filial_id.in_(unique_filial_ids),
                CashOut.mes_referencia.in_(unique_months)
            ).all()

            # Build lookup map: (filial_id, month, category) -> existing record
            existing_map = {
                (r.filial_id, r.mes_referencia, r.categoria): r
                for r in existing_records
            }
            logger.info(f"Found {len(existing_map)} existing records in database")

            # Separate updates and inserts
            to_update = []
            to_insert = []

            for (filial_id, month, category) in all_keys:
                budget_data = budget_agg.get((filial_id, month, category), {"amount": Decimal("0"), "filial_nome": "", "count": 0})
                actual_data = actual_agg.get((filial_id, month, category), {"amount": Decimal("0"), "filial_nome": "", "count": 0})

                filial_nome = budget_data["filial_nome"] or actual_data["filial_nome"] or internal_to_name.get(filial_id, f"Filial {filial_id}")

                existing = existing_map.get((filial_id, month, category))

                if existing:
                    # Mark for update - update object attributes directly
                    existing.orcamento = float(budget_data["amount"])
                    existing.realizado = float(actual_data["amount"])
                    existing.filial_nome = filial_nome
                    existing.detalhes = {
                        "budget_count": budget_data["count"],
                        "actual_count": actual_data["count"],
                        "source": "faturas_pagar"
                    }
                    to_update.append(existing)
                else:
                    # Mark for insert
                    new_record = CashOut(
                        filial_id=filial_id,
                        filial_nome=filial_nome,
                        mes_referencia=month,
                        categoria=category,
                        orcamento=float(budget_data["amount"]),
                        realizado=float(actual_data["amount"]),
                        detalhes={
                            "budget_count": budget_data["count"],
                            "actual_count": actual_data["count"],
                            "source": "faturas_pagar"
                        }
                    )
                    to_insert.append(new_record)

            logger.info(f"Bulk upsert: {len(to_update)} updates, {len(to_insert)} inserts")

            # Bulk insert new records
            if to_insert:
                self.db.bulk_save_objects(to_insert)

            # Updates are already tracked by SQLAlchemy (objects were modified in-place)
            # Commit all changes
            self.db.commit()

            count = len(to_update) + len(to_insert)

            logger.info(f"✅ Aggregated {count} CashOut records from FaturaPagar (SQL optimized)")
            return count

        except Exception as e:
            logger.error(f"Error aggregating CashOut from FaturaPagar: {e}", exc_info=True)
            self.db.rollback()
            raise

    # ============================================
    # Full Synchronization
    # ============================================

    def sync_all(
        self,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        development_ids: Optional[List[int]] = None,
        sync_developments: bool = True,
        sync_contracts: bool = True,
        sync_financial: bool = True,
        skip_recent_hours: int = 0,  # Skip developments synced within X hours (0 = process all)
    ) -> dict:
        """
        Perform full synchronization of all data with granular control.

        This method performs the complete workflow:
        1. Sync developments (sets is_active=False for all)
        2. Fetch contracts and save to database
        3. Update is_active=True for developments with active contracts
        4. Sync transactional data (CashIn, CashOut)

        Args:
            start_date: Start date for transactional data (defaults to 12 months ago)
            end_date: End date for transactional data (defaults to today)
            development_ids: Optional list of specific development IDs to sync
            sync_developments: If True, sync developments from API
            sync_contracts: If True, sync contracts from API
            sync_financial: If True, sync financial data (CashIn/CashOut)
            skip_recent_hours: Skip developments synced within X hours (0 = process all).
                              Uses `last_financial_sync_at` field for checkpoint/resume.

        Returns:
            Dict with sync statistics

        Raises:
            ValueError: If sync_financial=True but sync_developments or sync_contracts is False
        """
        # Validate dependencies
        if sync_financial and (not sync_developments or not sync_contracts):
            raise ValueError(
                "Cannot sync financial data without syncing developments and contracts. "
                "Set sync_developments=True and sync_contracts=True, or set sync_financial=False."
            )

        logger.info(
            f"Starting Mega API synchronization "
            f"(developments={sync_developments}, contracts={sync_contracts}, financial={sync_financial})"
        )

        # Default date range: last 2 months (from start of previous month)
        if end_date is None:
            end_date = date.today()
        if start_date is None:
            # Calculate first day of previous month
            # Example: if end_date = 2025-10-15, start_date = 2025-09-01
            first_day_current_month = end_date.replace(day=1)
            if first_day_current_month.month == 1:
                # If current month is January, previous month is December of previous year
                start_date = date(first_day_current_month.year - 1, 12, 1)
            else:
                start_date = date(first_day_current_month.year, first_day_current_month.month - 1, 1)

        stats = {
            "developments_synced": 0,
            "developments_skipped": 0,  # Skipped due to recent sync (checkpoint)
            "contracts_synced": 0,
            "cash_in_records": 0,
            "cash_out_records": 0,
            "errors": [],
            "timings": {},  # Tempo de cada etapa
        }

        sync_start_time = time.time()

        try:
            # STEP 1: Sync developments (and their filiais)
            # Always sync all developments since Mega API doesn't support filtering by ID
            if sync_developments:
                step1_start = time.time()
                logger.info("Step 1: Syncing all developments and filiais from API")
                stats["developments_synced"] = self.sync_developments()
                stats["timings"]["step1_developments"] = round(time.time() - step1_start, 2)
                logger.info(f"⏱️ Step 1 completed in {stats['timings']['step1_developments']:.2f}s")
            else:
                logger.info("Step 1: Skipping development sync (sync_developments=False)")

            # STEP 2: Get developments to process (only Mega developments!)
            query = self.db.query(Development).filter(Development.origem == "mega")

            if development_ids:
                query = query.filter(Development.id.in_(development_ids))

            developments = query.all()

            logger.info(f"Processing {len(developments)} Mega developments")

            # Track developments with active contracts
            developments_with_active_contracts = set()

            # STEP 3 & 4: Sync contracts and financial data together (optimized to fetch only once)
            if sync_contracts or sync_financial:
                if sync_financial and not sync_contracts:
                    # This shouldn't happen due to validation, but just in case
                    raise ValueError("Cannot sync financial without syncing contracts")

                logger.info("Step 2: Syncing contracts and financial data")

                # OPTIMIZATION: Fetch ALL contracts once instead of per-development
                step2_start = time.time()
                logger.info("🚀 Fetching ALL contracts from Mega API in a single call...")
                all_contratos = self.api_client.get_all_contratos()
                stats["timings"]["step2_fetch_contracts"] = round(time.time() - step2_start, 2)
                logger.info(f"✅ Fetched {len(all_contratos)} total contracts in {stats['timings']['step2_fetch_contracts']:.2f}s")

                # Group contracts by development ID
                contratos_by_dev = {}
                for contrato in all_contratos:
                    # Try both possible field names (API uses cod_empreendimento)
                    emp_id = contrato.get("cod_empreendimento") or contrato.get("empreendimento_id")
                    if emp_id:
                        if emp_id not in contratos_by_dev:
                            contratos_by_dev[emp_id] = []
                        contratos_by_dev[emp_id].append(contrato)

                logger.info(f"📊 Contracts grouped into {len(contratos_by_dev)} developments")

                # Free memory from all_contratos since we have contratos_by_dev now
                del all_contratos
                gc.collect()

                # OPTIMIZATION: Create dev lookup dict to avoid queries in loops
                dev_by_id = {dev.id: dev for dev in developments}

                # Pre-calculate months to process (for PortfolioStats and Delinquency)
                from dateutil.relativedelta import relativedelta
                months_to_process = []
                current_month = start_date.replace(day=1)
                end_month = end_date.replace(day=1)
                while current_month <= end_month:
                    months_to_process.append(current_month.strftime("%Y-%m"))
                    current_month = current_month + relativedelta(months=1)

                step3_start = time.time()
                devs_processed = 0
                devs_skipped = 0
                total_portfolio_stats = 0
                total_delinquency = 0
                cutoff_time = utc_now() - timedelta(hours=skip_recent_hours) if skip_recent_hours > 0 else None

                # Import models needed for inline processing
                from starke.infrastructure.database.models import PortfolioStats, Delinquency, Filial

                for dev in developments:
                    try:
                        dev_start = time.time()

                        # CHECKPOINT: Skip if recently synced
                        if cutoff_time and dev.last_financial_sync_at and dev.last_financial_sync_at > cutoff_time:
                            hours_ago = (utc_now() - dev.last_financial_sync_at).total_seconds() / 3600
                            logger.info(f"⏭️ Skipping {dev.name} - synced {hours_ago:.1f}h ago (within {skip_recent_hours}h)")
                            devs_skipped += 1
                            # Still count contracts for active status check
                            dev_contratos = contratos_by_dev.get(dev.external_id, [])
                            if any(self.config.is_contrato_ativo(c.get("status_contrato", "")) for c in dev_contratos):
                                developments_with_active_contracts.add(dev.id)
                            continue

                        logger.info(f"Processing development: {dev.name} (ID: {dev.id}, external_id: {dev.external_id})")

                        # Get contracts for this development from cache
                        # Note: contratos_by_dev is keyed by cod_empreendimento (external API ID)
                        dev_contratos = contratos_by_dev.get(dev.external_id, [])
                        logger.info(f"Found {len(dev_contratos)} contracts for {dev.name}")

                        # Sync CashIn using pre-fetched contracts
                        cash_in_result = self.sync_cash_in_for_development(
                            dev, start_date, end_date, pre_fetched_contratos=dev_contratos
                        )

                        stats["contracts_synced"] += cash_in_result["contracts_saved"]
                        stats["cash_in_records"] += cash_in_result["cash_in_records"]

                        # Get parcelas from result (will be used for PortfolioStats and Delinquency)
                        dev_parcelas = cash_in_result.get("parcelas", [])

                        # Check if this development has active contracts
                        # OPTIMIZATION: Use dev_contratos from cache instead of querying DB
                        # dev_contratos contains raw API data with status_contrato field
                        has_active = any(
                            self.config.is_contrato_ativo(c.get("status_contrato", ""))
                            for c in dev_contratos
                        )

                        if has_active:
                            developments_with_active_contracts.add(dev.id)

                        # ============================================
                        # MEMORY OPTIMIZATION: Process PortfolioStats and Delinquency inline
                        # This avoids keeping all parcelas in memory across developments
                        # ============================================
                        if sync_financial and has_active and dev_parcelas:
                            # Create cache for just this development
                            dev_cache = {dev.id: {"parcelas": dev_parcelas}}

                            # Calculate PortfolioStats for each month
                            for ref_month in months_to_process:
                                try:
                                    result = self.sync_balance_and_portfolio_stats_for_month(
                                        development_id=dev.id,
                                        development_name=dev.name,
                                        ref_month=ref_month,
                                        development_data_cache=dev_cache,
                                    )
                                    total_portfolio_stats += result["portfolio_stats_saved"]
                                except Exception as e:
                                    logger.error(f"Error calculating PortfolioStats for {dev.name} - {ref_month}: {e}")

                            # Calculate Delinquency for each month
                            for ref_month in months_to_process:
                                try:
                                    year, month = map(int, ref_month.split("-"))
                                    ref_date = date(year, month, 1)
                                    next_month_date = ref_date + relativedelta(months=1)
                                    last_day_of_month = next_month_date - relativedelta(days=1)

                                    delinquency_data = self.cash_flow_service.calculate_delinquency_from_parcelas(
                                        dev_parcelas,
                                        dev.id,
                                        dev.name,
                                        last_day_of_month
                                    )

                                    # Delete existing and insert new - ONLY MEGA
                                    self.db.query(Delinquency).filter(
                                        Delinquency.empreendimento_id == dev.id,
                                        Delinquency.ref_month == ref_month,
                                        Delinquency.origem == "mega"  # IMPORTANT: Only delete Mega records
                                    ).delete()

                                    delinquency = Delinquency(
                                        empreendimento_id=dev.id,
                                        empreendimento_nome=dev.name,
                                        ref_month=ref_month,
                                        up_to_30=delinquency_data.up_to_30,
                                        days_30_60=delinquency_data.days_30_60,
                                        days_60_90=delinquency_data.days_60_90,
                                        days_90_180=delinquency_data.days_90_180,
                                        above_180=delinquency_data.above_180,
                                        total=delinquency_data.total,
                                        details=delinquency_data.details,
                                    )
                                    self.db.add(delinquency)
                                    total_delinquency += 1
                                except Exception as e:
                                    logger.error(f"Error calculating Delinquency for {dev.name} - {ref_month}: {e}")

                            # Clear dev_cache to free memory
                            del dev_cache

                        # Activate development and filial after complete processing
                        if has_active:
                            dev.is_active = True
                            dev.updated_at = utc_now()
                            logger.info(f"✅ Activated development: {dev.name}")

                            # Also activate the filial if not already active
                            if dev.filial_id:
                                filial = self.db.query(Filial).filter(Filial.id == dev.filial_id).first()
                                if filial and not filial.is_active:
                                    filial.is_active = True
                                    filial.atualizado_em = utc_now()
                                    logger.info(f"✅ Activated filial: {filial.nome}")

                        # CHECKPOINT: Mark this development as synced
                        dev.last_financial_sync_at = utc_now()

                        # Commit after each development to avoid large transactions
                        self._safe_commit(f"dev_{dev.name}")

                        # MEMORY OPTIMIZATION: Clear parcelas from result to free memory
                        del dev_parcelas
                        cash_in_result.clear()

                        devs_processed += 1
                        dev_elapsed = time.time() - dev_start
                        logger.info(f"✅ {dev.name}: {dev_elapsed:.2f}s ({len(dev_contratos)} contracts)")

                        # MEMORY OPTIMIZATION: Run gc.collect() every 10 developments
                        if devs_processed % 10 == 0:
                            gc.collect()
                            logger.debug(f"Memory cleanup after {devs_processed} developments")

                    except Exception as e:
                        error_msg = f"Error syncing {dev.name}: {e}"
                        logger.error(error_msg)
                        stats["errors"].append(error_msg)

                        # Check if it's a database connection error
                        error_str = str(e).lower()
                        if "connection" in error_str or "closed" in error_str or "operational" in error_str or "rollback" in error_str:
                            logger.warning("Database connection lost, attempting to recover...")
                            try:
                                self.db.rollback()
                                # Test connection with a simple query
                                from sqlalchemy import text
                                self.db.execute(text("SELECT 1"))
                                logger.info("Database connection recovered after rollback")
                            except Exception as reconnect_error:
                                logger.error(f"Failed to recover database connection: {reconnect_error}")
                                raise  # Re-raise to stop the process
                        continue

                # Store inline-calculated stats
                stats["portfolio_stats_records"] = total_portfolio_stats
                stats["delinquency_records"] = total_delinquency

                stats["timings"]["step3_process_developments"] = round(time.time() - step3_start, 2)
                stats["developments_skipped"] = devs_skipped
                logger.info(f"⏱️ Step 3 completed: {devs_processed} processed, {devs_skipped} skipped in {stats['timings']['step3_process_developments']:.2f}s")
                logger.info(f"   PortfolioStats: {total_portfolio_stats}, Delinquency: {total_delinquency}")
                logger.info(f"   Activated {len(developments_with_active_contracts)} developments with active contracts")

                # STEP 5: Process Faturas a Pagar (accounts payable)
                # Faturas are not filtered by development - they are global across all filiais
                if sync_financial and developments_with_active_contracts:
                    step4_start = time.time()
                    logger.info(f"Step 4: Syncing Faturas a Pagar")
                    try:
                        faturas_count = self.sync_faturas_pagar(start_date, end_date)
                        stats["cash_out_records"] += faturas_count
                        stats["timings"]["step4_faturas_pagar"] = round(time.time() - step4_start, 2)
                        logger.info(f"⏱️ Synchronized {faturas_count} Faturas a Pagar in {stats['timings']['step4_faturas_pagar']:.2f}s")

                        # Aggregate faturas into SaidasCaixa
                        # Note: aggregate_cash_out_from_faturas processes all faturas in the DB
                        # No need to filter by date range as faturas were just synced for the period
                        agg_start = time.time()
                        logger.info("Step 4.1: Aggregating faturas into SaidasCaixa")
                        aggregate_count = self.aggregate_cash_out_from_faturas()
                        stats["timings"]["step4_1_aggregate_cashout"] = round(time.time() - agg_start, 2)
                        logger.info(f"⏱️ Aggregated {aggregate_count} SaidasCaixa in {stats['timings']['step4_1_aggregate_cashout']:.2f}s")
                    except Exception as e:
                        error_msg = f"Error syncing Faturas a Pagar: {e}"
                        logger.error(error_msg)
                        stats["errors"].append(error_msg)

            else:
                logger.info("Step 2-3: Skipping contract and financial sync (all disabled)")

            # NOTE: PortfolioStats and Delinquency are now calculated inline in the main loop
            # for memory optimization (avoids keeping all parcelas in memory across developments)

            # Calculate total time
            stats["timings"]["total"] = round(time.time() - sync_start_time, 2)
            total_minutes = stats["timings"]["total"] / 60

            logger.info("=" * 60)
            logger.info("Synchronization completed successfully")
            logger.info(f"⏱️ TOTAL TIME: {stats['timings']['total']:.2f}s ({total_minutes:.1f} min)")
            logger.info("=" * 60)
            logger.info(f"Statistics: {stats}")

            return stats

        except Exception as e:
            logger.error(f"Fatal error during synchronization: {e}")
            raise

    # ============================================
    # Portfolio Stats & Delinquency Synchronization
    # ============================================

    def sync_portfolio_stats_for_development(
        self, development: Development, ref_date: Optional[date] = None
    ) -> bool:
        """
        Calculate and save portfolio statistics and delinquency for a development.

        Args:
            development: Development to calculate stats for
            ref_date: Reference date (defaults to today)

        Returns:
            True if successful
        """
        from starke.infrastructure.database.models import PortfolioStats, Delinquency

        if ref_date is None:
            ref_date = date.today()

        logger.info(f"Calculating portfolio stats for {development.name} on {ref_date}")

        try:
            # Get encrypted ID
            encrypted_id = development.raw_data.get("id") or development.raw_data.get("est_in_codigo_encrypt")

            if not encrypted_id:
                logger.error(f"No encrypted ID for development {development.name}")
                return False

            # Fetch contracts and parcelas
            contratos = self.api_client.get_contratos(encrypted_id)
            logger.info(f"Found {len(contratos)} contracts for {development.name}")

            # Collect all parcelas from all contracts
            todas_parcelas = []
            for contrato in contratos:
                try:
                    cod_contrato = contrato.get("cod_contrato")
                    if not cod_contrato:
                        continue

                    parcelas = self.api_client.get_parcelas_by_contract_id(int(cod_contrato))
                    todas_parcelas.extend(parcelas)
                except Exception as e:
                    logger.warning(f"Error fetching parcelas for contract {contrato.get('cod_contrato')}: {e}")
                    continue

            logger.info(f"Collected {len(todas_parcelas)} total parcelas")

            # Calculate portfolio statistics
            stats = self.calculator.calculate_portfolio_stats(
                contratos=contratos,
                parcelas=todas_parcelas,
                ref_date=ref_date,
            )

            # Clear existing stats for this date - ONLY MEGA
            self.db.query(PortfolioStats).filter(
                PortfolioStats.empreendimento_id == development.id,
                PortfolioStats.ref_month == ref_date.isoformat(),
                PortfolioStats.origem == "mega"  # IMPORTANT: Only delete Mega records, not UAU
            ).delete()

            # Save portfolio stats
            portfolio_stats = PortfolioStats(
                empreendimento_id=development.id,
                empreendimento_nome=development.name,
                ref_date=ref_date.isoformat(),
                vp=stats["vp"],
                ltv=stats["ltv"],
                prazo_medio=stats["prazo_medio"],
                duration=stats["duration"],
                total_contracts=stats["total_contracts"],
                active_contracts=stats["active_contracts"],
                details={"calculation_date": utc_now().isoformat()},
            )
            self.db.add(portfolio_stats)

            # Calculate delinquency
            delinquency_data = self.cash_flow_service.calculate_delinquency_from_parcelas(
                todas_parcelas,
                development.id,
                development.name,
                ref_date
            )

            # Clear existing delinquency for this date - ONLY MEGA
            self.db.query(Delinquency).filter(
                Delinquency.empreendimento_id == development.id,
                Delinquency.ref_month == ref_date.isoformat(),
                Delinquency.origem == "mega"  # IMPORTANT: Only delete Mega records, not UAU
            ).delete()

            # Save delinquency
            delinquency = Delinquency(
                empreendimento_id=development.id,
                empreendimento_nome=development.name,
                ref_month=ref_date.isoformat(),
                up_to_30=delinquency_data.up_to_30,
                days_30_60=delinquency_data.days_30_60,
                days_60_90=delinquency_data.days_60_90,
                days_90_180=delinquency_data.days_90_180,
                above_180=delinquency_data.above_180,
                total=delinquency_data.total,
                details={
                    "delinquency_rate": self.calculator.calculate_delinquency_rate(
                        delinquency_data.total, stats["vp"]
                    )
                },
            )
            self.db.add(delinquency)

            self.db.commit()

            logger.info(
                f"Saved portfolio stats for {development.name}: "
                f"VP={stats['vp']:,.2f}, LTV={stats['ltv']:.2f}%, Duration={stats['duration']:.2f}y"
            )

            return True

        except Exception as e:
            logger.error(f"Error calculating portfolio stats for {development.name}: {e}")
            self.db.rollback()
            return False

    def sync_balance_and_portfolio_stats_for_month(
        self,
        development_id: int,
        development_name: str,
        ref_month: str,
        development_data_cache: Optional[dict] = None,
    ) -> dict:
        """
        Calculate and save PortfolioStats for a specific month from existing database records.

        NOTE: Balance calculation has been REMOVED due to granularity mismatch:
        - CashIn is aggregated by empreendimento
        - CashOut is aggregated by filial (from faturas_pagar)
        - Cannot accurately calculate empreendimento-level balance since CashOut is at filial level
        - The saldos table has been dropped via migration 10e24d47b737

        This method now only calculates:
        - PortfolioStats from Contract data

        Args:
            development_id: Development ID
            development_name: Development name
            ref_month: Reference month in YYYY-MM format
            development_data_cache: Optional cache with parcelas data

        Returns:
            Dict with counts: {balance_saved, portfolio_stats_saved}
        """
        from starke.infrastructure.database.models import (
            Contract,
            PortfolioStats,
        )
        from dateutil.relativedelta import relativedelta

        logger.info(f"Calculating PortfolioStats for {development_name} - {ref_month}")

        result = {"balance_saved": 0, "portfolio_stats_saved": 0}

        try:
            # Parse ref_month to get date
            year, month = map(int, ref_month.split("-"))
            ref_date = date(year, month, 1)
            # Get last day of month
            next_month = ref_date + relativedelta(months=1)
            last_day_of_month = (next_month - relativedelta(days=1))

            # ============================================
            # BALANCE CALCULATION REMOVED
            # ============================================
            # Balance calculation has been removed due to granularity mismatch.
            # CashOut is at filial level, CashIn is at empreendimento level.
            # Cannot accurately calculate empreendimento-level balance.
            # The saldos table was dropped via migration 10e24d47b737_remove_saldos_table.py
            #
            # If balance reporting is needed in the future, consider:
            # 1. Calculating balance at filial level instead
            # 2. Adding empreendimento_id to faturas_pagar table
            # 3. Creating a separate balance tracking mechanism
            # ============================================

            # ============================================
            # STEP 2: Calculate PortfolioStats from Contracts
            # ============================================

            # Get all contracts for this development
            contracts = (
                self.db.query(Contract)
                .filter(Contract.empreendimento_id == development_id)
                .all()
            )

            if contracts:
                # Convert contracts to dict format for calculator
                contratos_data = []
                todas_parcelas = []

                # Get parcelas from cache if available
                if development_data_cache and development_id in development_data_cache:
                    cached_parcelas = development_data_cache[development_id].get("parcelas", [])
                    todas_parcelas = cached_parcelas
                    logger.info(f"Using {len(todas_parcelas)} parcelas from cache for portfolio stats")

                for contract in contracts:
                    # Build contract dict using NEW API field names
                    # Note: Contract model doesn't have 'prazo_meses' field
                    contrato_dict = {
                        "cod_contrato": contract.cod_contrato,  # Required for matching with parcelas
                        "status_contrato": contract.status,
                        "valor_contrato": float(contract.valor_contrato) if contract.valor_contrato else 0.0,
                        "valor_atualizado_ipca": float(contract.valor_atualizado_ipca) if contract.valor_atualizado_ipca else None,
                        "prazo_meses": 0,  # Not available in Contract model
                    }
                    contratos_data.append(contrato_dict)

                # Calculate portfolio statistics using PortfolioCalculator
                stats = self.calculator.calculate_portfolio_stats(
                    contratos=contratos_data,
                    parcelas=todas_parcelas,
                    ref_date=last_day_of_month,
                )

                # Clear existing stats for this month - ONLY MEGA
                self.db.query(PortfolioStats).filter(
                    PortfolioStats.empreendimento_id == development_id,
                    PortfolioStats.ref_month == ref_month,
                    PortfolioStats.origem == "mega"  # IMPORTANT: Only delete Mega records
                ).delete()

                # Save portfolio stats
                portfolio_stats = PortfolioStats(
                    empreendimento_id=development_id,
                    empreendimento_nome=development_name,
                    ref_month=ref_month,
                    vp=stats["vp"],
                    ltv=stats["ltv"],
                    prazo_medio=stats["prazo_medio"],
                    duration=stats["duration"],
                    total_contracts=stats["total_contracts"],
                    active_contracts=stats["active_contracts"],
                    details={"calculation_date": utc_now().isoformat()},
                )
                self.db.add(portfolio_stats)
                result["portfolio_stats_saved"] = 1

                logger.info(
                    f"Calculated PortfolioStats for {development_name} - {ref_month}: "
                    f"VP={stats['vp']:,.2f}, LTV={stats['ltv']:.2f}%, Duration={stats['duration']:.2f}y"
                )
            else:
                logger.warning(f"No contracts found for {development_name}, skipping PortfolioStats")

            # Commit all changes
            self.db.commit()

            return result

        except Exception as e:
            logger.error(
                f"Error calculating Balance/PortfolioStats for {development_name} - {ref_month}: {e}",
                exc_info=True,
            )
            self.db.rollback()
            return result

    # ============================================
    # Helper Methods
    # ============================================
    