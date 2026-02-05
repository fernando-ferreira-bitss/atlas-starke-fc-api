"""Data ingestion service with idempotency."""

import hashlib
import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, datetime
from typing import Any, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from starke.core.logging import get_logger
from starke.domain.services.contract_service import ContractService
from starke.infrastructure.database.models import RawPayload
from starke.infrastructure.external_apis.mega_client import MegaAPIClient

logger = get_logger(__name__)


class IngestionService:
    """Service for ingesting data from external APIs with idempotency."""

    def __init__(self, session: Session, api_client: MegaAPIClient) -> None:
        """
        Initialize ingestion service.

        Args:
            session: Database session
            api_client: Mega API client
        """
        self.session = session
        self.api_client = api_client
        self.contract_service = ContractService(session, api_client)

        # Cache for despesas/receitas to avoid multiple API calls in same period
        self._despesas_cache: Optional[dict[str, list[dict[str, Any]]]] = None
        self._receitas_cache: Optional[dict[str, list[dict[str, Any]]]] = None

    def _generate_payload_hash(self, payload: dict[str, Any]) -> str:
        """
        Generate hash for payload to ensure idempotency.

        Args:
            payload: Data payload

        Returns:
            SHA-256 hash of the payload
        """
        # Sort keys to ensure consistent hashing
        payload_str = json.dumps(payload, sort_keys=True, default=str)
        return hashlib.sha256(payload_str.encode()).hexdigest()

    def _is_payload_processed(self, source: str, exec_date: str, payload_hash: str) -> bool:
        """
        Check if payload was already processed.

        Args:
            source: Data source identifier
            exec_date: Execution date
            payload_hash: Payload hash

        Returns:
            True if already processed, False otherwise
        """
        stmt = select(RawPayload).where(
            RawPayload.source == source,
            RawPayload.exec_date == exec_date,
            RawPayload.payload_hash == payload_hash,
        )
        result = self.session.execute(stmt).first()
        return result is not None

    def _store_raw_payload(
        self,
        source: str,
        exec_date: str,
        payload: dict[str, Any],
        payload_hash: str,
    ) -> RawPayload:
        """
        Store raw payload in database.

        Args:
            source: Data source identifier
            exec_date: Execution date
            payload: Data payload
            payload_hash: Payload hash

        Returns:
            Created RawPayload record
        """
        raw_payload = RawPayload(
            source=source,
            exec_date=exec_date,
            payload_hash=payload_hash,
            payload_json=payload,
            created_at=datetime.utcnow(),
        )
        self.session.add(raw_payload)
        self.session.flush()

        logger.info(
            "Stored raw payload",
            source=source,
            exec_date=exec_date,
            payload_id=raw_payload.id,
        )
        return raw_payload

    def ingest_contratos_by_empreendimento(
        self, empreendimento_id: int, exec_date: date
    ) -> list[dict[str, Any]]:
        """
        Ingest contracts for an empreendimento with idempotency.

        Args:
            empreendimento_id: Empreendimento ID
            exec_date: Execution date

        Returns:
            List of contract data
        """
        source = f"contratos_emp_{empreendimento_id}"
        exec_date_str = exec_date.isoformat()

        logger.info(
            "Starting contract ingestion",
            source=source,
            exec_date=exec_date_str,
        )

        # Fetch data from API
        contratos = self.api_client.get_contratos_by_empreendimento(empreendimento_id)

        if not contratos:
            logger.warning(
                "No contracts found",
                empreendimento_id=empreendimento_id,
                exec_date=exec_date_str,
            )
            return []

        # Create payload wrapper with metadata
        payload = {
            "empreendimento_id": empreendimento_id,
            "exec_date": exec_date_str,
            "timestamp": datetime.utcnow().isoformat(),
            "count": len(contratos),
            "data": contratos,
        }

        payload_hash = self._generate_payload_hash(payload)

        # Check idempotency
        if self._is_payload_processed(source, exec_date_str, payload_hash):
            logger.info(
                "Payload already processed (idempotent)",
                source=source,
                exec_date=exec_date_str,
                payload_hash=payload_hash,
            )
            return contratos

        # Store raw payload
        self._store_raw_payload(source, exec_date_str, payload, payload_hash)

        logger.info(
            "Contract ingestion completed",
            source=source,
            exec_date=exec_date_str,
            count=len(contratos),
        )

        return contratos

    def ingest_parcelas_by_contrato(
        self, contrato_id: int, exec_date: date
    ) -> list[dict[str, Any]]:
        """
        Ingest installments for a contract with idempotency.

        Args:
            contrato_id: Contract ID
            exec_date: Execution date

        Returns:
            List of installment data
        """
        source = f"parcelas_cto_{contrato_id}"
        exec_date_str = exec_date.isoformat()

        logger.info(
            "Starting installment ingestion",
            source=source,
            exec_date=exec_date_str,
        )

        # Fetch data from API
        parcelas = self.api_client.get_parcelas_by_contrato(contrato_id)

        if not parcelas:
            logger.warning(
                "No installments found",
                contrato_id=contrato_id,
                exec_date=exec_date_str,
            )
            return []

        # Create payload wrapper
        payload = {
            "contrato_id": contrato_id,
            "exec_date": exec_date_str,
            "timestamp": datetime.utcnow().isoformat(),
            "count": len(parcelas),
            "data": parcelas,
        }

        payload_hash = self._generate_payload_hash(payload)

        # Check idempotency
        if self._is_payload_processed(source, exec_date_str, payload_hash):
            logger.info(
                "Payload already processed (idempotent)",
                source=source,
                exec_date=exec_date_str,
                payload_hash=payload_hash,
            )
            return parcelas

        # Store raw payload
        self._store_raw_payload(source, exec_date_str, payload, payload_hash)

        logger.info(
            "Installment ingestion completed",
            source=source,
            exec_date=exec_date_str,
            count=len(parcelas),
        )

        return parcelas

    def _get_all_despesas_for_period(self, first_day: date, last_day: date) -> list[dict[str, Any]]:
        """
        Get ALL despesas from all filiais for a period (with caching).

        This method caches the result to avoid multiple API calls when processing
        multiple empreendimentos in the same period.

        Args:
            first_day: Start date
            last_day: End date

        Returns:
            List of all despesas
        """
        cache_key = f"{first_day.isoformat()}_{last_day.isoformat()}"

        if self._despesas_cache is None:
            self._despesas_cache = {}

        if cache_key not in self._despesas_cache:
            logger.info(
                "Fetching all despesas from API (cache miss)",
                date_range=f"{first_day.isoformat()} to {last_day.isoformat()}",
            )
            despesas = self.api_client.get_despesas(
                data_inicio=first_day.isoformat(),
                data_fim=last_day.isoformat(),
            )
            self._despesas_cache[cache_key] = despesas
            logger.info(
                "Cached all despesas",
                count=len(despesas),
                cache_key=cache_key,
            )
        else:
            despesas = self._despesas_cache[cache_key]
            logger.debug(
                "Using cached despesas",
                count=len(despesas),
                cache_key=cache_key,
            )

        return despesas

    def ingest_despesas_by_empreendimento(
        self, empreendimento_id: int, exec_date: date
    ) -> list[dict[str, Any]]:
        """
        Ingest despesas (contas a pagar) for an empreendimento with idempotency.

        Uses contracts to filter despesas: Agente.Codigo must match an active contract
        from this empreendimento.

        Args:
            empreendimento_id: Empreendimento ID
            exec_date: Execution date

        Returns:
            List of despesas data filtered by active contracts

        Note:
            Fetches data for the entire month of exec_date.
            Uses cached despesas to avoid multiple API calls when processing multiple empreendimentos.
        """
        source = f"despesas_emp_{empreendimento_id}"
        exec_date_str = exec_date.isoformat()

        # Calculate date range for the month
        first_day = exec_date.replace(day=1)
        if exec_date.month == 12:
            last_day = exec_date.replace(year=exec_date.year + 1, month=1, day=1)
        else:
            last_day = exec_date.replace(month=exec_date.month + 1, day=1)

        # Subtract one day to get last day of current month
        from datetime import timedelta
        last_day = last_day - timedelta(days=1)

        logger.info(
            "Starting despesas ingestion",
            source=source,
            exec_date=exec_date_str,
            empreendimento_id=empreendimento_id,
            date_range=f"{first_day.isoformat()} to {last_day.isoformat()}",
        )

        # Get ALL despesas (cached if already fetched for this period)
        all_despesas = self._get_all_despesas_for_period(first_day, last_day)

        # Get active contracts for this empreendimento
        active_contract_codes = self.contract_service.get_active_contract_codes(empreendimento_id)

        if not active_contract_codes:
            logger.warning(
                "No active contracts found for empreendimento",
                empreendimento_id=empreendimento_id,
                exec_date=exec_date_str,
            )
            return []

        # Filter despesas by Agente.Codigo matching active contracts
        contract_codes_set = set(active_contract_codes)
        despesas = [
            d for d in all_despesas
            if d.get("Agente", {}).get("Codigo") in contract_codes_set
        ]

        logger.info(
            "Filtered despesas by active contracts",
            total_despesas=len(all_despesas),
            filtered_count=len(despesas),
            active_contracts=len(active_contract_codes),
            empreendimento_id=empreendimento_id,
        )

        if not despesas:
            logger.warning(
                "No despesas found after filtering by contracts",
                empreendimento_id=empreendimento_id,
                active_contracts=len(active_contract_codes),
                exec_date=exec_date_str,
            )
            return []

        # Create payload wrapper with metadata
        payload = {
            "empreendimento_id": empreendimento_id,
            "exec_date": exec_date_str,
            "date_range": {
                "start": first_day.isoformat(),
                "end": last_day.isoformat(),
            },
            "active_contracts_count": len(active_contract_codes),
            "timestamp": datetime.utcnow().isoformat(),
            "count": len(despesas),
            "data": despesas,
        }

        payload_hash = self._generate_payload_hash(payload)

        # Check idempotency
        if self._is_payload_processed(source, exec_date_str, payload_hash):
            logger.info(
                "Payload already processed (idempotent)",
                source=source,
                exec_date=exec_date_str,
                payload_hash=payload_hash,
            )
            return despesas

        # Store raw payload
        self._store_raw_payload(source, exec_date_str, payload, payload_hash)

        logger.info(
            "Despesas ingestion completed",
            source=source,
            exec_date=exec_date_str,
            count=len(despesas),
        )

        return despesas

    def ingest_all_for_date(
        self, empreendimento_ids: list[int], exec_date: date
    ) -> dict[str, Any]:
        """
        Ingest all data for multiple empreendimentos for a specific date.

        Args:
            empreendimento_ids: List of empreendimento IDs
            exec_date: Execution date

        Returns:
            Summary of ingested data
        """
        logger.info(
            "Starting full ingestion",
            empreendimento_count=len(empreendimento_ids),
            exec_date=exec_date.isoformat(),
        )

        summary = {
            "exec_date": exec_date.isoformat(),
            "empreendimentos": [],
            "total_contracts": 0,
            "total_installments": 0,
            "errors": [],
        }

        for emp_id in empreendimento_ids:
            try:
                # Ingest contracts for empreendimento
                contratos = self.ingest_contratos_by_empreendimento(emp_id, exec_date)
                contract_count = len(contratos)
                installment_count = 0

                # Extract contract IDs
                contrato_ids = []
                for contrato in contratos:
                    contrato_id = (
                        contrato.get("cod_contrato")
                        or contrato.get("codigo_contrato")
                        or contrato.get("codigoContrato")
                    )
                    if contrato_id:
                        contrato_ids.append(contrato_id)

                # Ingest installments for each contract IN PARALLEL (much faster!)
                logger.info(
                    "Starting parallel installment ingestion",
                    empreendimento_id=emp_id,
                    contract_count=len(contrato_ids),
                )

                with ThreadPoolExecutor(max_workers=10) as executor:
                    # Submit all tasks
                    future_to_id = {
                        executor.submit(self.ingest_parcelas_by_contrato, cto_id, exec_date): cto_id
                        for cto_id in contrato_ids
                    }

                    # Collect results as they complete
                    for future in as_completed(future_to_id):
                        cto_id = future_to_id[future]
                        try:
                            parcelas = future.result()
                            installment_count += len(parcelas)
                        except Exception as e:
                            logger.error(
                                "Failed to ingest parcelas for contract",
                                contrato_id=cto_id,
                                error=str(e),
                            )

                # Ingest despesas for empreendimento
                despesas_count = 0
                try:
                    despesas = self.ingest_despesas_by_empreendimento(
                        emp_id, exec_date
                    )
                    despesas_count = len(despesas)
                except Exception as e:
                    logger.error(
                        "Failed to ingest despesas for empreendimento",
                        empreendimento_id=emp_id,
                        error=str(e),
                    )

                summary["empreendimentos"].append(
                    {
                        "id": emp_id,
                        "contracts": contract_count,
                        "installments": installment_count,
                        "despesas": despesas_count,
                    }
                )
                summary["total_contracts"] += contract_count
                summary["total_installments"] += installment_count

                logger.info(
                    "Empreendimento ingestion completed",
                    empreendimento_id=emp_id,
                    contracts=contract_count,
                    installments=installment_count,
                    despesas=despesas_count,
                )

            except Exception as e:
                error_msg = f"Error ingesting empreendimento {emp_id}: {str(e)}"
                logger.error(error_msg, empreendimento_id=emp_id, error=str(e))
                summary["errors"].append(error_msg)

        logger.info(
            "Full ingestion completed",
            total_contracts=summary["total_contracts"],
            total_installments=summary["total_installments"],
            error_count=len(summary["errors"]),
        )

        return summary
