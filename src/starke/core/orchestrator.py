"""Main orchestrator for the cash flow report workflow."""

from datetime import date, datetime
from typing import Any, Optional

from starke.core.config import get_settings
from starke.core.logging import get_logger
from starke.domain.entities.cash_flow import CashOutData
from starke.domain.services.cash_flow_service import CashFlowService
from starke.domain.services.development_service import DevelopmentService
from starke.infrastructure.database.base import get_session
from starke.infrastructure.database.models import Run
from starke.infrastructure.external_apis.mega_client import MegaAPIClient

logger = get_logger(__name__)


class Orchestrator:
    """Orchestrates the complete cash flow report workflow."""

    def __init__(self) -> None:
        """Initialize orchestrator."""
        logger.info("Orchestrator initialized")

    def execute(
        self,
        ref_date: date,
        empreendimento_ids: Optional[list[int]] = None,
        dry_run: bool = False,
        skip_ingestion: bool = False,
    ) -> dict[str, Any]:
        """
        Execute complete workflow.

        Args:
            ref_date: Reference date (T-1)
            empreendimento_ids: List of empreendimento IDs to process (None = all)
            dry_run: If True, don't send emails
            skip_ingestion: If True, skip data ingestion (use existing data)

        Returns:
            Execution summary
        """
        ref_date_str = ref_date.isoformat()
        logger.info(
            "Starting workflow execution",
            ref_date=ref_date_str,
            empreendimento_ids=empreendimento_ids,
            dry_run=dry_run,
            skip_ingestion=skip_ingestion,
        )

        with get_session() as session:
            # Create run record
            run = Run(
                exec_date=ref_date_str,
                status="running",
                started_at=datetime.utcnow(),
            )
            session.add(run)
            session.flush()

            try:
                summary = self._execute_workflow(
                    session=session,
                    ref_date=ref_date,
                    empreendimento_ids=empreendimento_ids,
                    dry_run=dry_run,
                    skip_ingestion=skip_ingestion,
                )

                # Update run as successful
                run.status = "success"
                run.finished_at = datetime.utcnow()
                run.metrics = summary
                session.commit()

                logger.info("Workflow execution completed successfully", summary=summary)
                return summary

            except Exception as e:
                # Update run as failed
                run.status = "failed"
                run.finished_at = datetime.utcnow()
                run.error = str(e)
                session.commit()

                logger.error("Workflow execution failed", error=str(e), exc_info=True)
                raise

    def _execute_workflow(
        self,
        session: Any,
        ref_date: date,
        empreendimento_ids: Optional[list[int]],
        dry_run: bool,
        skip_ingestion: bool,
    ) -> dict[str, Any]:
        """Execute the workflow steps."""
        summary: dict[str, Any] = {
            "ref_date": ref_date.isoformat(),
            "empreendimentos_count": 0,
            "total_contracts": 0,
            "total_installments": 0,
            "errors": [],
        }

        # Step 0: Sync developments from Mega API (if not provided manually)
        if not empreendimento_ids:
            logger.info("Step 0: Syncing developments from Mega API")
            dev_service = DevelopmentService(session)
            sync_result = dev_service.sync_from_mega_api()

            logger.info(
                "Developments sync completed",
                created=sync_result["created"],
                updated=sync_result["updated"],
                total=sync_result["total"],
                errors=len(sync_result["errors"]),
            )

            if sync_result["errors"]:
                summary["errors"].extend(sync_result["errors"])

            # Get active developments from database
            active_devs = dev_service.get_all_developments(active_only=True)
            empreendimento_ids = [dev.id for dev in active_devs]

            logger.info(
                "Active developments loaded",
                count=len(empreendimento_ids),
                ids=empreendimento_ids,
            )

            if not empreendimento_ids:
                error_msg = "No active developments found in database"
                logger.error(error_msg)
                summary["errors"].append(error_msg)
                return summary

        # Step 1: Data Ingestion (if not skipped)
        # NOTE: IngestionService was removed - data ingestion is now handled by sync services
        if not skip_ingestion:
            logger.info("Step 1: Data ingestion - using sync services")
            # TODO: Implement data ingestion using MegaSyncService or UauSyncService
        else:
            logger.info("Step 1: Data ingestion skipped")

        # Step 2: Process Cash Flow Calculations
        logger.info("Step 2: Cash flow calculations")
        cash_flow_service = CashFlowService(session)

        for emp_id in empreendimento_ids:
            try:
                self._process_empreendimento(
                    cash_flow_service=cash_flow_service,
                    empreendimento_id=emp_id,
                    ref_date=ref_date,
                )
                summary["empreendimentos_count"] += 1

            except Exception as e:
                error_msg = f"Error processing empreendimento {emp_id}: {str(e)}"
                logger.error(error_msg, empreendimento_id=emp_id, error=str(e))
                summary["errors"].append(error_msg)

        return summary

    def _process_empreendimento(
        self,
        cash_flow_service: CashFlowService,
        empreendimento_id: int,
        ref_date: date,
    ) -> None:
        """Process cash flow for a single empreendimento."""
        logger.info(
            "Processing empreendimento",
            empreendimento_id=empreendimento_id,
            ref_date=ref_date.isoformat(),
        )

        # Fetch ingested data from database
        from starke.infrastructure.database.models import RawPayload
        from sqlalchemy import select

        # Get contracts for this empreendimento
        # Note: API returns ALL data (not filtered by date), so we get the most recent payload
        source = f"contratos_emp_{empreendimento_id}"
        stmt = select(RawPayload).where(
            RawPayload.source == source
        ).order_by(RawPayload.created_at.desc()).limit(1)

        result = cash_flow_service.session.execute(stmt).scalar_one_or_none()

        contratos = []
        if result and result.payload_json:
            contratos = result.payload_json.get("data", [])

        # Get empreendimento name from Development table
        from starke.infrastructure.database.models import Development
        development = cash_flow_service.session.execute(
            select(Development).where(Development.id == empreendimento_id)
        ).scalar_one_or_none()
        empreendimento_nome = development.name if development else f"Empreendimento {empreendimento_id}"

        # Get all parcelas for all contracts in ONE query (much faster!)
        # Note: API returns ALL parcelas (not filtered by date), so we get the most recent payload
        all_parcelas = []

        # Build list of sources for all contracts
        contrato_ids = [c.get("cod_contrato") for c in contratos if c.get("cod_contrato")]
        parcelas_sources = [f"parcelas_cto_{cid}" for cid in contrato_ids]

        if parcelas_sources:
            # Fetch all parcelas in a single query using DISTINCT ON
            from sqlalchemy import func
            stmt = (
                select(RawPayload)
                .where(RawPayload.source.in_(parcelas_sources))
                .order_by(RawPayload.source, RawPayload.created_at.desc())
                .distinct(RawPayload.source)
            )

            parcelas_results = cash_flow_service.session.execute(stmt).scalars().all()

            # Aggregate all parcelas
            for result in parcelas_results:
                if result and result.payload_json:
                    all_parcelas.extend(result.payload_json.get("data", []))

        # Calculate cash in from parcelas
        cash_in_list = cash_flow_service.calculate_cash_in_from_parcelas(
            parcelas=all_parcelas,
            empreendimento_id=empreendimento_id,
            empreendimento_nome=empreendimento_nome,
            ref_date=ref_date,
        )

        # Get despesas (cash out) data
        source_despesas = f"despesas_emp_{empreendimento_id}"
        stmt_despesas = (
            select(RawPayload)
            .where(RawPayload.source == source_despesas)
            .order_by(RawPayload.created_at.desc())
            .limit(1)
        )

        despesas_result = cash_flow_service.session.execute(stmt_despesas).scalar_one_or_none()

        all_despesas = []
        if despesas_result and despesas_result.payload_json:
            all_despesas = despesas_result.payload_json.get("data", [])

        # Calculate cash out from despesas
        cash_out_list = cash_flow_service.calculate_cash_out_from_despesas(
            despesas=all_despesas,
            contratos=contratos,  # Pass contratos for empreendimento filtering
            empreendimento_id=empreendimento_id,
            empreendimento_nome=empreendimento_nome,
            ref_date=ref_date,
        )

        # Calculate portfolio stats
        portfolio_stats = cash_flow_service.calculate_portfolio_stats(
            contratos=contratos,
            empreendimento_id=empreendimento_id,
            empreendimento_nome=empreendimento_nome,
            ref_date=ref_date,
            parcelas=all_parcelas,  # Pass parcelas for VP calculation using vlr_presente
        )

        # NOTE: Balance calculation removed - saldos table dropped due to granularity mismatch
        # CashOut is at filial level, CashIn is at empreendimento level
        # Cannot accurately calculate balance at empreendimento level

        # balance = cash_flow_service.calculate_balance(
        #     cash_in_list=cash_in_list,
        #     cash_out_list=cash_out_list,
        #     empreendimento_id=empreendimento_id,
        #     empreendimento_nome=empreendimento_nome,
        #     ref_date=ref_date,
        # )

        # Save to database (without balance)
        # NOTE: save_cash_flow_data also tries to save balance - this may fail
        # Consider refactoring to not require balance parameter
        # cash_flow_service.save_cash_flow_data(
        #     cash_in_list=cash_in_list,
        #     cash_out_list=cash_out_list,
        #     balance=balance,
        #     portfolio_stats=portfolio_stats,
        # )
