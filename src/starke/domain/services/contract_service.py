"""Contract service for fetching and managing contracts from Mega API."""

from datetime import datetime, date
from decimal import Decimal
from typing import Any, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from starke.core.logging import get_logger
from starke.domain.entities.contracts import ContratoData
from starke.infrastructure.database.models import Contract, Development
from starke.infrastructure.external_apis.mega_client import MegaAPIClient

logger = get_logger(__name__)


class ContractService:
    """Service for managing contracts."""

    def __init__(self, db_session: Session, api_client: MegaAPIClient) -> None:
        """Initialize contract service.

        Args:
            db_session: Database session
            api_client: Mega API client
        """
        self.db = db_session
        self.api_client = api_client

    def fetch_and_save_contracts(self, empreendimento_ids: list[int]) -> dict[str, Any]:
        """Fetch contracts from API for given developments and save to database.

        NOTE: Processes sequentially to avoid 429 rate limiting from Mega API.
        The parallelization is now only used for parcelas (many calls per development).

        Args:
            empreendimento_ids: List of development IDs to fetch contracts for

        Returns:
            Dictionary with statistics about the operation
        """
        logger.info(
            "Starting contract fetch and save (sequential processing)",
            empreendimento_count=len(empreendimento_ids),
        )

        stats = {
            "total_developments": len(empreendimento_ids),
            "developments_processed": 0,
            "contracts_fetched": 0,
            "contracts_saved": 0,
            "contracts_deleted": 0,
            "errors": 0,
        }

        # Process sequentially to avoid 429 rate limiting
        for emp_id in empreendimento_ids:
            try:
                result = self._fetch_and_save_one(emp_id)
                stats["developments_processed"] += 1
                stats["contracts_fetched"] += result["fetched"]
                stats["contracts_saved"] += result["saved"]
                stats["contracts_deleted"] += result["deleted"]

                if result["fetched"] > 0:
                    logger.info(
                        "Processed empreendimento",
                        empreendimento_id=emp_id,
                        contracts=result["fetched"],
                        saved=result["saved"],
                        deleted=result["deleted"],
                        progress=f"{stats['developments_processed']}/{stats['total_developments']}",
                    )
            except Exception as e:
                logger.error(
                    "Error processing empreendimento",
                    empreendimento_id=emp_id,
                    error=str(e),
                )
                stats["errors"] += 1

        logger.info("Contract fetch and save completed", **stats)
        return stats

    def _fetch_and_save_one(self, empreendimento_id: int) -> dict[str, int]:
        """Fetch and save contracts for a single empreendimento.

        Each thread creates its own database session to avoid concurrent access issues.
        Uses DELETE + INSERT strategy to ensure database matches API.

        Args:
            empreendimento_id: Development ID

        Returns:
            Dictionary with counts of fetched, saved, and deleted contracts
        """
        from starke.infrastructure.database.base import get_session

        try:
            # Fetch contracts from API
            contracts_data = self._fetch_contracts_for_development(empreendimento_id)

            if contracts_data:
                # Create a new session for this thread (thread-safe)
                with get_session() as session:
                    # Save to database using thread-local session
                    saved, deleted = self._save_contracts_thread_safe(
                        session, contracts_data
                    )
                    return {
                        "fetched": len(contracts_data),
                        "saved": saved,
                        "deleted": deleted,
                    }

            return {"fetched": 0, "saved": 0, "deleted": 0}

        except Exception as e:
            logger.error(
                "Error in _fetch_and_save_one",
                empreendimento_id=empreendimento_id,
                error=str(e),
            )
            raise

    def _fetch_contracts_for_development(self, empreendimento_id: int) -> list[dict[str, Any]]:
        """Fetch contracts from API for a single development.

        Args:
            empreendimento_id: Development ID

        Returns:
            List of contract data dictionaries
        """
        try:
            endpoint = f"/api/Carteira/DadosContrato/IdEmpreendimento={empreendimento_id}"
            result = self.api_client._request("GET", endpoint)

            if isinstance(result, list):
                return result
            return []

        except Exception as e:
            logger.error(
                "Failed to fetch contracts",
                empreendimento_id=empreendimento_id,
                error=str(e),
            )
            raise

    def _save_contracts_thread_safe(
        self, session: Session, contracts_data: list[dict[str, Any]]
    ) -> tuple[int, int]:
        """Save contracts to database using provided session (thread-safe).

        Strategy: DELETE all contracts for the empreendimentos, then INSERT new ones.
        This ensures the database always reflects exactly what's in the API.

        Args:
            session: Database session to use
            contracts_data: List of contract data from API

        Returns:
            Tuple of (saved_count, deleted_count)
        """
        if not contracts_data:
            logger.debug("No contracts to save")
            return 0, 0

        saved_count = 0
        deleted_count = 0

        logger.info(
            "Saving contracts to database",
            total_contracts=len(contracts_data),
        )

        # Get unique empreendimento IDs from the data
        empreendimento_ids = list(set(
            c.get("cod_empreendimento")
            for c in contracts_data
            if c.get("cod_empreendimento")
        ))

        # DELETE all existing contracts for these empreendimentos
        from sqlalchemy import delete
        delete_stmt = delete(Contract).where(
            Contract.empreendimento_id.in_(empreendimento_ids)
        )
        result = session.execute(delete_stmt)
        deleted_count = result.rowcount

        logger.info(
            "Deleted existing contracts",
            deleted_count=deleted_count,
            empreendimentos=len(empreendimento_ids),
        )

        # Find earliest data_assinatura to fetch IPCA data once
        earliest_date = None
        active_contracts_with_dates = [
            c for c in contracts_data
            if c.get("status_contrato") == "Ativo" and c.get("data_assinatura")
        ]

        ipca_data = {}
        if active_contracts_with_dates:
            try:
                # Parse dates to find earliest
                from datetime import datetime as dt
                parsed_dates = []
                for c in active_contracts_with_dates:
                    try:
                        d = dt.strptime(c["data_assinatura"], "%d/%m/%Y").date()
                        parsed_dates.append(d)
                    except:
                        continue

                if parsed_dates:
                    earliest_date = min(parsed_dates)

                    # Fetch IPCA data ONCE for all contracts
                    from starke.domain.services.ipca_service import IPCAService
                    ipca_service = IPCAService()
                    ipca_data = ipca_service.fetch_ipca_data(earliest_date, date.today())

                    logger.info(
                        "Fetched IPCA data once for all active contracts",
                        earliest_date=earliest_date.isoformat(),
                        ipca_months=len(ipca_data),
                        active_contracts=len(active_contracts_with_dates),
                    )
            except Exception as e:
                logger.error("Failed to fetch IPCA data", error=str(e))

        # INSERT all new contracts
        for contract_dict in contracts_data:
            try:
                cod_contrato = contract_dict.get("cod_contrato")
                empreendimento_id = contract_dict.get("cod_empreendimento")

                if not cod_contrato or not empreendimento_id:
                    logger.warning(
                        "Skipping contract with missing IDs",
                        contract=contract_dict,
                    )
                    continue

                # Parse data_assinatura if present
                data_assinatura = None
                if contract_dict.get("data_assinatura"):
                    try:
                        # API returns date in DD/MM/YYYY format
                        from datetime import datetime as dt
                        data_assinatura = dt.strptime(contract_dict["data_assinatura"], "%d/%m/%Y").date()
                    except (ValueError, TypeError):
                        logger.warning(
                            "Failed to parse data_assinatura",
                            raw_value=contract_dict.get("data_assinatura"),
                        )

                # Calculate IPCA-adjusted value for ACTIVE contracts only
                valor_atualizado_ipca = None
                status = contract_dict.get("status_contrato")
                valor_contrato = contract_dict.get("valor_contrato")

                if status == "Ativo" and ipca_data and data_assinatura and valor_contrato:
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
                            "Calculated IPCA for contract",
                            cod_contrato=cod_contrato,
                            valor_original=float(valor_contrato),
                            valor_atualizado=float(valor_atualizado_ipca),
                            accumulated_ipca=float(accumulated_percentage),
                        )
                    except Exception as e:
                        logger.error(
                            "Failed to calculate IPCA for contract",
                            cod_contrato=cod_contrato,
                            error=str(e),
                        )

                # Create new contract
                contract_data = {
                    "cod_contrato": cod_contrato,
                    "empreendimento_id": empreendimento_id,
                    "status": status,
                    "valor_contrato": valor_contrato,
                    "valor_atualizado_ipca": valor_atualizado_ipca,
                    "data_assinatura": data_assinatura,
                    "last_synced_at": datetime.utcnow(),
                }

                contract = Contract(**contract_data)
                session.add(contract)
                saved_count += 1

            except Exception as e:
                logger.error(
                    "Error saving contract",
                    contract=contract_dict,
                    error=str(e),
                )
                continue

        # Commit the contract changes (IPCA already calculated inline)
        session.commit()
        logger.info(
            "Committed contract changes to database",
            saved=saved_count,
            deleted=deleted_count,
        )

        # Update empreendimento is_active based on contract status
        self._update_empreendimento_active_status(session, empreendimento_ids)

        return saved_count, deleted_count

    def _update_ipca_adjusted_values(
        self, session: Session, empreendimento_ids: list[int]
    ) -> None:
        """Calculate and update IPCA-adjusted values for contracts.

        Updates valor_atualizado_ipca for contracts that have both
        valor_contrato and data_assinatura.

        OPTIMIZED: Makes only ONE call to BCB API regardless of number of contracts.

        Args:
            session: Database session to use
            empreendimento_ids: List of empreendimento IDs to update
        """
        from starke.domain.services.ipca_service import IPCAService

        # Get contracts that need IPCA calculation
        contracts_to_update = session.execute(
            select(Contract).where(
                Contract.empreendimento_id.in_(empreendimento_ids),
                Contract.valor_contrato.isnot(None),
                Contract.data_assinatura.isnot(None),
            )
        ).scalars().all()

        if not contracts_to_update:
            logger.debug("No contracts need IPCA calculation")
            return

        logger.info(
            "Calculating IPCA-adjusted values",
            num_contracts=len(contracts_to_update),
        )

        # Find earliest data_assinatura to minimize API calls
        earliest_date = min(c.data_assinatura for c in contracts_to_update)

        # Make ONE call to BCB API for entire period
        ipca_service = IPCAService()
        ipca_data = ipca_service.fetch_ipca_data(earliest_date, date.today())

        logger.info(
            "Fetched IPCA data once for all contracts",
            earliest_date=earliest_date.isoformat(),
            ipca_months=len(ipca_data),
        )

        updated_count = 0

        for contract in contracts_to_update:
            try:
                # Calculate accumulated IPCA for this contract's period
                accumulated = Decimal("1")
                for month_key in sorted(ipca_data.keys()):
                    # Parse month_key (YYYY-MM) to compare with contract date
                    month_date = datetime.strptime(month_key + "-01", "%Y-%m-%d").date()

                    # Only accumulate IPCA from contract date onwards
                    if month_date >= contract.data_assinatura.replace(day=1):
                        ipca_monthly = ipca_data[month_key]
                        accumulated *= (Decimal("1") + ipca_monthly / Decimal("100"))

                # Calculate adjusted value
                accumulated_percentage = (accumulated - Decimal("1")) * Decimal("100")
                adjusted_value = Decimal(str(contract.valor_contrato)) * (Decimal("1") + accumulated_percentage / Decimal("100"))

                contract.valor_atualizado_ipca = adjusted_value
                updated_count += 1

                logger.debug(
                    "Updated IPCA-adjusted value",
                    cod_contrato=contract.cod_contrato,
                    valor_original=float(contract.valor_contrato),
                    valor_atualizado=float(adjusted_value),
                    data_assinatura=contract.data_assinatura.isoformat(),
                    accumulated_ipca=float(accumulated_percentage),
                )

            except Exception as e:
                logger.error(
                    "Failed to calculate IPCA for contract",
                    cod_contrato=contract.cod_contrato,
                    error=str(e),
                )
                continue

        # Commit IPCA updates
        if updated_count > 0:
            session.commit()
            logger.info(
                "Updated IPCA-adjusted values",
                updated_count=updated_count,
            )

    def _update_empreendimento_active_status(
        self, session: Session, empreendimento_ids: list[int]
    ) -> None:
        """Update empreendimento is_active flag based on contract status.

        Sets is_active = True if the empreendimento has at least one contract
        with status = 'Ativo'.

        Args:
            session: Database session to use
            empreendimento_ids: List of empreendimento IDs to check
        """
        for emp_id in empreendimento_ids:
            # Check if this empreendimento has any active contracts
            has_active = session.execute(
                select(Contract.id)
                .where(Contract.empreendimento_id == emp_id)
                .where(Contract.status == "Ativo")
                .limit(1)
            ).first() is not None

            # Update the Development record
            development = session.execute(
                select(Development).where(Development.id == emp_id)
            ).scalar_one_or_none()

            if development:
                development.is_active = has_active
                development.updated_at = datetime.utcnow()

                logger.debug(
                    "Updated empreendimento active status",
                    empreendimento_id=emp_id,
                    is_active=has_active,
                )

        # Commit the development updates
        session.commit()
        logger.info(
            "Updated empreendimento active status for all developments",
            empreendimentos=len(empreendimento_ids),
        )

    def _save_contracts(self, contracts_data: list[dict[str, Any]]) -> tuple[int, int]:
        """Save contracts to database (using self.db session - not thread-safe).

        Args:
            contracts_data: List of contract data from API

        Returns:
            Tuple of (saved_count, updated_count)
        """
        return self._save_contracts_thread_safe(self.db, contracts_data)

    def _save_contracts_old(self, contracts_data: list[dict[str, Any]]) -> tuple[int, int]:
        """DEPRECATED: Old implementation kept for reference.

        Args:
            contracts_data: List of contract data from API

        Returns:
            Tuple of (saved_count, updated_count)
        """
        saved_count = 0
        updated_count = 0

        logger.info(
            "Saving contracts to database",
            total_contracts=len(contracts_data),
        )

        for contract_dict in contracts_data:
            try:
                cod_contrato = contract_dict.get("cod_contrato")
                empreendimento_id = contract_dict.get("cod_empreendimento")

                if not cod_contrato or not empreendimento_id:
                    logger.warning(
                        "Skipping contract with missing IDs",
                        contract=contract_dict,
                    )
                    continue

                # Check if contract already exists
                existing = self.db.execute(
                    select(Contract).where(
                        Contract.cod_contrato == cod_contrato,
                        Contract.empreendimento_id == empreendimento_id,
                    )
                ).scalar_one_or_none()

                # Only save essential fields
                contract_data = {
                    "cod_contrato": cod_contrato,
                    "empreendimento_id": empreendimento_id,
                    "status": contract_dict.get("status_contrato"),
                    "last_synced_at": datetime.utcnow(),
                }

                if existing:
                    # Update existing contract
                    for key, value in contract_data.items():
                        setattr(existing, key, value)
                    updated_count += 1
                    logger.debug(
                        "Updated existing contract",
                        cod_contrato=cod_contrato,
                        empreendimento_id=empreendimento_id,
                    )
                else:
                    # Create new contract
                    contract = Contract(**contract_data)
                    self.db.add(contract)
                    saved_count += 1
                    logger.info(
                        "Added new contract",
                        cod_contrato=cod_contrato,
                        empreendimento_id=empreendimento_id,
                        status=contract_data.get("status"),
                    )

            except Exception as e:
                logger.error(
                    "Error saving contract",
                    contract=contract_dict,
                    error=str(e),
                )
                continue

        # Commit all changes
        if saved_count > 0 or updated_count > 0:
            self.db.commit()
            logger.info(
                "Committed contract changes",
                saved=saved_count,
                updated=updated_count,
            )
        else:
            logger.debug("No contracts to commit")

        return saved_count, updated_count

    def get_active_developments(self) -> list[int]:
        """Get list of active development IDs.

        A development is considered active if it has at least one contract with status = 'Ativo'.
        Note: 'teste' developments are filtered out when saving, no need to filter here.

        Returns:
            List of active development IDs
        """
        stmt = (
            select(Contract.empreendimento_id)
            .where(Contract.status == "Ativo")
            .distinct()
        )

        result = self.db.execute(stmt)
        active_emp_ids = [row[0] for row in result.all()]

        logger.info(
            "Retrieved active developments",
            count=len(active_emp_ids),
        )

        return active_emp_ids

    def get_active_contract_codes(self, empreendimento_id: Optional[int] = None) -> list[int]:
        """Get list of active contract codes.

        Args:
            empreendimento_id: Optional filter by development ID

        Returns:
            List of contract codes (cod_contrato)
        """
        stmt = (
            select(Contract.cod_contrato)
            .where(Contract.status == "Ativo")
        )

        if empreendimento_id:
            stmt = stmt.where(Contract.empreendimento_id == empreendimento_id)

        result = self.db.execute(stmt)
        contract_codes = [row[0] for row in result.all()]

        logger.info(
            "Retrieved active contract codes",
            count=len(contract_codes),
            empreendimento_id=empreendimento_id,
        )

        return contract_codes

    def get_contracts_by_development(self, empreendimento_id: int) -> list[Contract]:
        """Get all contracts for a development.

        Args:
            empreendimento_id: Development ID

        Returns:
            List of Contract models
        """
        stmt = select(Contract).where(Contract.empreendimento_id == empreendimento_id)
        result = self.db.execute(stmt)
        return list(result.scalars().all())

    def get_contract_count_by_status(self) -> dict[str, int]:
        """Get count of contracts by status.

        Returns:
            Dictionary with status as key and count as value
        """
        from sqlalchemy import func

        stmt = select(Contract.status, func.count(Contract.id)).group_by(Contract.status)

        result = self.db.execute(stmt)
        counts = {status or "Unknown": count for status, count in result.all()}

        return counts
