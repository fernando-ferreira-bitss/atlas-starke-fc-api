"""Scheduler service for automated daily synchronization."""

import logging
import os
from datetime import date, datetime, timedelta
from typing import Optional

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from starke.domain.services.mega_sync_service import MegaSyncService
from starke.domain.services.uau_sync_service import UAUSyncService
from starke.core.date_helpers import utc_now
from starke.infrastructure.database.base import get_session
from starke.infrastructure.database.models import Run

logger = logging.getLogger(__name__)


class SyncScheduler:
    """Scheduler for automated daily synchronization from Mega and UAU APIs."""

    def __init__(self):
        """Initialize the scheduler."""
        self.scheduler = BackgroundScheduler()
        self.timezone = os.getenv("REPORT_TIMEZONE", "America/Sao_Paulo")

        # Get schedule from environment or default to 00:00
        run_at = os.getenv("RUN_AT") or os.getenv("EXECUTION_TIME", "00:00")
        hour, minute = map(int, run_at.split(":"))

        self.schedule_hour = hour
        self.schedule_minute = minute

        logger.info(
            f"Scheduler initialized: will run at {self.schedule_hour:02d}:{self.schedule_minute:02d} "
            f"({self.timezone})"
        )

    def start(self):
        """Start the scheduler."""
        # Job 1: Daily Mega sync (runs every day at configured time)
        self.scheduler.add_job(
            func=self.run_mega_sync,
            trigger=CronTrigger(
                hour=self.schedule_hour,
                minute=self.schedule_minute,
                timezone=self.timezone
            ),
            id="daily_mega_sync",
            name="Daily Mega Synchronization",
            replace_existing=True,
            max_instances=1,
        )
        logger.info(
            f"Mega sync scheduled: daily at {self.schedule_hour:02d}:{self.schedule_minute:02d}"
        )

        # Job 2: Weekly UAU sync (runs only on Saturday at 00:00)
        self.scheduler.add_job(
            func=self.run_uau_sync,
            trigger=CronTrigger(
                day_of_week="sat",  # Saturday
                hour=0,
                minute=0,
                timezone=self.timezone
            ),
            id="weekly_uau_sync",
            name="Weekly UAU Synchronization (Saturday)",
            replace_existing=True,
            max_instances=1,
        )
        logger.info("UAU sync scheduled: Saturday at 00:00")

        self.scheduler.start()
        logger.info("Scheduler started successfully")

    def stop(self):
        """Stop the scheduler."""
        if self.scheduler.running:
            self.scheduler.shutdown(wait=True)
            logger.info("Scheduler stopped")

    def run_mega_sync(self):
        """
        Execute daily Mega synchronization.

        Runs every day at the scheduled time.
        Processes data for T-1 (yesterday).
        """
        exec_date = (date.today() - timedelta(days=1)).isoformat()
        logger.info(f"Starting daily Mega sync for date: {exec_date}")

        mega_run_id = self._create_run_record(exec_date, source="mega")
        try:
            mega_stats = self._execute_mega_sync(exec_date)
            logger.info(f"Mega sync completed: {mega_stats}")
            self._complete_run_record(mega_run_id, status="success", metrics=mega_stats)

            # Run aggregation after Mega sync
            try:
                self._execute_aggregation(exec_date)
                logger.info("Aggregation completed successfully")
            except Exception as e:
                logger.error(f"Aggregation failed: {e}", exc_info=True)

        except Exception as e:
            error_msg = f"Mega sync failed: {e}"
            logger.error(error_msg, exc_info=True)
            self._complete_run_record(mega_run_id, status="failed", error=str(e), metrics={"error": str(e)})

    def run_uau_sync(self):
        """
        Execute weekly UAU synchronization.

        Runs only on Saturday at 00:00.
        Processes data for the last 12 months.
        """
        exec_date = (date.today() - timedelta(days=1)).isoformat()
        logger.info(f"Starting weekly UAU sync for date: {exec_date}")

        uau_run_id = self._create_run_record(exec_date, source="uau")
        try:
            uau_stats = self._execute_uau_sync(exec_date)
            logger.info(f"UAU sync completed: {uau_stats}")
            self._complete_run_record(uau_run_id, status="success", metrics=uau_stats)

            # Run aggregation after UAU sync
            try:
                self._execute_aggregation(exec_date)
                logger.info("Aggregation completed successfully")
            except Exception as e:
                logger.error(f"Aggregation failed: {e}", exc_info=True)

        except Exception as e:
            error_msg = f"UAU sync failed: {e}"
            logger.error(error_msg, exc_info=True)
            self._complete_run_record(uau_run_id, status="failed", error=str(e), metrics={"error": str(e)})

    def run_daily_sync(self):
        """
        Execute both Mega and UAU synchronization (legacy method for manual runs).

        Runs Mega first, then UAU sequentially.
        """
        exec_date = (date.today() - timedelta(days=1)).isoformat()
        logger.info(f"Starting combined sync for date: {exec_date}")

        mega_success = False
        uau_success = False

        # Step 1: Execute Mega synchronization
        mega_run_id = self._create_run_record(exec_date, source="mega")
        try:
            logger.info("Step 1: Starting Mega synchronization...")
            mega_stats = self._execute_mega_sync(exec_date)
            logger.info(f"Mega sync completed: {mega_stats}")
            self._complete_run_record(mega_run_id, status="success", metrics=mega_stats)
            mega_success = True
        except Exception as e:
            error_msg = f"Mega sync failed: {e}"
            logger.error(error_msg, exc_info=True)
            self._complete_run_record(mega_run_id, status="failed", error=str(e), metrics={"error": str(e)})

        # Step 2: Execute UAU synchronization
        uau_run_id = self._create_run_record(exec_date, source="uau")
        try:
            logger.info("Step 2: Starting UAU synchronization...")
            uau_stats = self._execute_uau_sync(exec_date)
            logger.info(f"UAU sync completed: {uau_stats}")
            self._complete_run_record(uau_run_id, status="success", metrics=uau_stats)
            uau_success = True
        except Exception as e:
            error_msg = f"UAU sync failed: {e}"
            logger.error(error_msg, exc_info=True)
            self._complete_run_record(uau_run_id, status="failed", error=str(e), metrics={"error": str(e)})

        # Step 3: Execute monthly aggregation
        if mega_success or uau_success:
            try:
                self._execute_aggregation(exec_date)
                logger.info("Aggregation completed successfully")
            except Exception as e:
                logger.error(f"Aggregation failed: {e}", exc_info=True)

        # Log final summary
        if mega_success and uau_success:
            logger.info(f"Combined sync completed successfully for {exec_date}")
        elif mega_success or uau_success:
            logger.warning(f"Combined sync completed with partial success for {exec_date}")
        else:
            logger.error(f"Combined sync failed for {exec_date}")

    def _create_run_record(
        self,
        exec_date: str,
        source: str = "mega",
        triggered_by_user_id: Optional[int] = None
    ) -> int:
        """Create a run record in the database.

        Args:
            exec_date: Date in YYYY-MM-DD format
            source: Data source ('mega' or 'uau')
            triggered_by_user_id: User ID who triggered the sync (None = scheduler)
        """
        with get_session() as db:
            run = Run(
                exec_date=exec_date,
                source=source,
                status="running",
                started_at=utc_now(),
                triggered_by_user_id=triggered_by_user_id,
            )
            db.add(run)
            db.commit()
            db.refresh(run)

            trigger_info = f"user_id={triggered_by_user_id}" if triggered_by_user_id else "scheduler"
            logger.info(f"Created run record: ID={run.id}, source={source}, exec_date={exec_date}, triggered_by={trigger_info}")
            return run.id

    def _complete_run_record(
        self,
        run_id: int,
        status: str,
        error: Optional[str] = None,
        metrics: Optional[dict] = None
    ):
        """Update run record with completion status."""
        with get_session() as db:
            run = db.query(Run).filter(Run.id == run_id).first()
            if run:
                run.status = status
                run.finished_at = utc_now()
                run.error = error
                run.metrics = metrics or {}
                db.commit()

                logger.info(f"Updated run record: ID={run_id}, status={status}")

    def _execute_mega_sync(self, exec_date: str) -> dict:
        """
        Execute the Mega API synchronization.

        This method performs the full sync workflow using the optimized MegaSyncService:
        1. Sync developments (sets is_active=False for all)
        2. Sync contracts and save to database (single fetch, saves contracts + processes parcelas)
        3. Update is_active=True for developments with active contracts
        4. Sync transactional data (CashIn, CashOut) only for active developments

        Args:
            exec_date: Date to sync in YYYY-MM-DD format

        Returns:
            Statistics dictionary
        """
        from starke.infrastructure.external_apis.mega_api_client import MegaAPIClient

        # Parse date
        exec_date_obj = date.fromisoformat(exec_date)

        # Calculate date range (sync last 2 months of data)
        end_date = exec_date_obj
        start_date = end_date - timedelta(days=60)

        logger.info(f"[Mega] Syncing data from {start_date} to {end_date}")

        try:
            with get_session() as db:
                with MegaAPIClient() as api_client:
                    # Use MegaSyncService for the complete optimized workflow
                    with MegaSyncService(db, api_client) as sync_service:
                        # sync_all performs all steps:
                        # 1. Sync developments
                        # 2. Fetch and save contracts (one fetch per development)
                        # 3. Update is_active flags
                        # 4. Process financial data (CashIn/CashOut) for active developments only
                        stats = sync_service.sync_all(
                            start_date=start_date,
                            end_date=end_date,
                            sync_developments=True,
                            sync_contracts=True,
                            sync_financial=True,
                        )

            logger.info("[Mega] Synchronization completed successfully")
            logger.info(f"[Mega] Statistics: {stats}")

            return stats

        except Exception as e:
            logger.error(f"[Mega] Error during synchronization: {e}", exc_info=True)
            raise

    def _execute_uau_sync(self, exec_date: str) -> dict:
        """
        Execute the UAU API synchronization.

        This method performs the full sync workflow using the UAUSyncService:
        1. Sync empresas (developments)
        2. Sync CashOut (desembolsos)
        3. Sync CashIn (parcelas)
        4. Sync PortfolioStats
        5. Sync Delinquency

        Args:
            exec_date: Date to sync in YYYY-MM-DD format

        Returns:
            Statistics dictionary
        """
        from starke.infrastructure.external_apis.uau_api_client import UAUAPIClient

        # Parse date
        exec_date_obj = date.fromisoformat(exec_date)

        # Calculate date range (sync last 12 months of data)
        end_date = exec_date_obj
        start_date = date(end_date.year - 1, end_date.month, 1)

        logger.info(f"[UAU] Syncing data from {start_date} to {end_date}")

        try:
            with get_session() as db:
                with UAUAPIClient() as api_client:
                    sync_service = UAUSyncService(db, api_client)
                    # sync_all performs all steps for all empresas
                    stats = sync_service.sync_all(
                        start_date=start_date,
                        end_date=end_date,
                    )

            logger.info("[UAU] Synchronization completed successfully")
            logger.info(f"[UAU] Statistics: {stats}")

            return stats

        except Exception as e:
            logger.error(f"[UAU] Error during synchronization: {e}", exc_info=True)
            raise

    def _execute_aggregation(self, exec_date: str):
        """
        Execute monthly aggregation after sync.

        Args:
            exec_date: Date to aggregate in YYYY-MM-DD format
        """
        logger.info(f"Starting monthly aggregation for {exec_date}")

        # Import aggregation function
        import subprocess
        import sys
        from pathlib import Path

        # Get project root
        project_root = Path(__file__).parent.parent.parent.parent
        script_path = project_root / "scripts" / "aggregate_monthly_data.py"

        # Run aggregation script
        result = subprocess.run(
            [sys.executable, str(script_path)],
            env={**os.environ, "PYTHONPATH": f"{project_root / 'src'}:{os.environ.get('PYTHONPATH', '')}"},
            capture_output=True,
            text=True
        )

        if result.returncode != 0:
            logger.error(f"Aggregation failed: {result.stderr}")
            raise RuntimeError(f"Aggregation failed: {result.stderr}")

        logger.info("Monthly aggregation completed successfully")
        logger.debug(f"Aggregation output: {result.stdout}")

    def run_manual_sync(self, exec_date: Optional[str] = None, triggered_by_user_id: Optional[int] = None):
        """
        Manually trigger a sync (useful for testing or re-running).

        Runs Mega first, then UAU sequentially. Each sync is independent -
        if one fails, the other still executes. Creates separate Run records
        for each source to allow individual error tracking.

        Args:
            exec_date: Optional date in YYYY-MM-DD format. Defaults to yesterday.
            triggered_by_user_id: User ID who triggered the sync.
        """
        if exec_date is None:
            exec_date = (date.today() - timedelta(days=1)).isoformat()

        logger.info(f"Manual sync triggered for date: {exec_date} by user_id={triggered_by_user_id}")

        mega_success = False
        uau_success = False

        # Step 1: Execute Mega synchronization (independent record)
        mega_run_id = self._create_run_record(exec_date, source="mega", triggered_by_user_id=triggered_by_user_id)
        try:
            logger.info("Step 1: Starting Mega synchronization...")
            mega_stats = self._execute_mega_sync(exec_date)
            logger.info(f"Mega sync completed: {mega_stats}")
            self._complete_run_record(mega_run_id, status="success", metrics=mega_stats)
            mega_success = True
        except Exception as e:
            error_msg = f"Mega sync failed: {e}"
            logger.error(error_msg, exc_info=True)
            self._complete_run_record(mega_run_id, status="failed", error=str(e), metrics={"error": str(e)})

        # Step 2: Execute UAU synchronization (independent record)
        uau_run_id = self._create_run_record(exec_date, source="uau", triggered_by_user_id=triggered_by_user_id)
        try:
            logger.info("Step 2: Starting UAU synchronization...")
            uau_stats = self._execute_uau_sync(exec_date)
            logger.info(f"UAU sync completed: {uau_stats}")
            self._complete_run_record(uau_run_id, status="success", metrics=uau_stats)
            uau_success = True
        except Exception as e:
            error_msg = f"UAU sync failed: {e}"
            logger.error(error_msg, exc_info=True)
            self._complete_run_record(uau_run_id, status="failed", error=str(e), metrics={"error": str(e)})

        # Step 3: Execute monthly aggregation (only if at least one sync succeeded)
        if mega_success or uau_success:
            try:
                self._execute_aggregation(exec_date)
                logger.info("Aggregation completed successfully")
            except Exception as e:
                error_msg = f"Aggregation failed: {e}"
                logger.error(error_msg, exc_info=True)

        # Log final summary
        if mega_success and uau_success:
            logger.info(f"Manual sync completed successfully for {exec_date}")
        elif mega_success or uau_success:
            logger.warning(f"Manual sync completed with partial success for {exec_date}")
        else:
            logger.error(f"Manual sync failed for {exec_date}")


# Global scheduler instance
_scheduler: Optional[SyncScheduler] = None


def get_scheduler() -> SyncScheduler:
    """Get or create the global scheduler instance."""
    global _scheduler
    if _scheduler is None:
        _scheduler = SyncScheduler()
    return _scheduler


def start_scheduler():
    """Start the global scheduler."""
    scheduler = get_scheduler()
    scheduler.start()


def stop_scheduler():
    """Stop the global scheduler."""
    global _scheduler
    if _scheduler is not None:
        _scheduler.stop()
        _scheduler = None
