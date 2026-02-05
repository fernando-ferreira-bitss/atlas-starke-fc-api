"""Scheduler API routes - JSON endpoints."""

import logging
from datetime import date, datetime
from typing import List, Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from starke.api.dependencies import get_current_active_user, get_db
from starke.core.scheduler import get_scheduler
from starke.infrastructure.database.models import Run, User

from .schemas import (
    RunResponse,
    RunListResponse,
    SchedulerStatus,
    SyncOrigin,
    SyncRequest,
    SyncResponse,
    TriggerResponse,
)

router = APIRouter(prefix="/scheduler", tags=["Scheduler"])
logger = logging.getLogger(__name__)


@router.get("/status", response_model=SchedulerStatus)
def get_scheduler_status(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> SchedulerStatus:
    """
    Retorna status do scheduler e próxima execução.
    """
    scheduler = get_scheduler()

    # Get next run time
    jobs = scheduler.scheduler.get_jobs()
    next_run = None
    if jobs:
        daily_sync_job = next((j for j in jobs if j.id == "daily_mega_sync"), None)
        if daily_sync_job:
            next_run = daily_sync_job.next_run_time.isoformat() if daily_sync_job.next_run_time else None

    return SchedulerStatus(
        running=scheduler.scheduler.running,
        next_run=next_run,
        schedule=f"{scheduler.schedule_hour:02d}:{scheduler.schedule_minute:02d}",
        timezone=scheduler.timezone,
    )


@router.get("/runs", response_model=RunListResponse)
def get_recent_runs(
    page: int = Query(1, ge=1, description="Página"),
    per_page: int = Query(20, ge=1, le=100, description="Itens por página"),
    status: Optional[str] = Query(None, description="Filtrar por status (success, failed, running)"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> RunListResponse:
    """
    Retorna execuções recentes do sync com paginação.
    """
    query = db.query(Run)

    # Filtro por status
    if status:
        query = query.filter(Run.status == status)

    # Total de registros
    total = query.count()

    # Paginação
    offset = (page - 1) * per_page
    runs = query.order_by(Run.started_at.desc()).offset(offset).limit(per_page).all()

    items = [
        RunResponse(
            id=run.id,
            exec_date=str(run.exec_date),
            status=run.status,
            started_at=run.started_at.isoformat(),
            finished_at=run.finished_at.isoformat() if run.finished_at else None,
            duration_seconds=(
                round((run.finished_at - run.started_at).total_seconds(), 2) if run.finished_at else None
            ),
            error=run.error,
            metrics=run.metrics,
            triggered_by_user_id=run.triggered_by_user_id,
        )
        for run in runs
    ]

    return RunListResponse(
        items=items,
        total=total,
        page=page,
        per_page=per_page,
        pages=(total + per_page - 1) // per_page if total > 0 else 0,
    )


@router.get("/runs/{run_id}", response_model=RunResponse)
def get_run_details(
    run_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> RunResponse:
    """
    Retorna detalhes de uma execução específica.
    """
    run = db.query(Run).filter(Run.id == run_id).first()

    if not run:
        raise HTTPException(status_code=404, detail="Execução não encontrada")

    return RunResponse(
        id=run.id,
        exec_date=str(run.exec_date),
        status=run.status,
        started_at=run.started_at.isoformat(),
        finished_at=run.finished_at.isoformat() if run.finished_at else None,
        duration_seconds=(
            round((run.finished_at - run.started_at).total_seconds(), 2) if run.finished_at else None
        ),
        error=run.error,
        metrics=run.metrics,
        triggered_by_user_id=run.triggered_by_user_id,
    )


@router.post("/trigger", response_model=TriggerResponse)
def trigger_manual_sync(
    exec_date: Optional[str] = Query(None, description="Data no formato YYYY-MM-DD (default: T-1)"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> TriggerResponse:
    """
    Dispara sincronização manual (Mega apenas - legacy).

    - **exec_date**: Data para sincronização (default: ontem/T-1)
    """
    scheduler = get_scheduler()

    try:
        logger.info(f"Manual sync triggered by user {current_user.email} (id={current_user.id}) for date: {exec_date or 'T-1'}")
        scheduler.run_manual_sync(exec_date, triggered_by_user_id=current_user.id)

        return TriggerResponse(
            status="success",
            message=f"Sync job triggered for date: {exec_date or 'T-1'}",
        )
    except Exception as e:
        logger.error(f"Failed to trigger manual sync: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Falha ao disparar sync: {str(e)}")


def _run_sync_task(
    origem: SyncOrigin,
    start_date: Optional[date],
    end_date: Optional[date],
    empresa_ids: Optional[List[int]],
    user_id: int,
    user_email: str,
) -> dict:
    """
    Execute sync task in background.

    Returns dict with stats from sync operations.
    """
    from starke.infrastructure.database.base import SessionLocal
    from starke.infrastructure.external_apis.mega_api_client import MegaAPIClient
    from starke.infrastructure.external_apis.uau_api_client import UAUAPIClient
    from starke.domain.services.mega_sync_service import MegaSyncService
    from starke.domain.services.uau_sync_service import UAUSyncService

    stats = {"mega": None, "uau": None}

    # Default dates
    if end_date is None:
        end_date = date.today()
    if start_date is None:
        start_date = date(end_date.year - 1, end_date.month, 1)

    logger.info(f"Sync task started by {user_email} (id={user_id}): origem={origem}, period={start_date} to {end_date}")

    with SessionLocal() as db:
        # Create Run record
        run = Run(
            exec_date=end_date.isoformat(),
            status="running",
            started_at=datetime.utcnow(),
            triggered_by_user_id=user_id,
        )
        db.add(run)
        db.commit()
        db.refresh(run)
        run_id = run.id
        logger.info(f"Created run record: ID={run_id}, triggered_by_user_id={user_id}")

        try:
            # Sync Mega
            if origem in (SyncOrigin.MEGA, SyncOrigin.BOTH):
                try:
                    logger.info("Starting Mega sync...")
                    with MegaAPIClient() as mega_client:
                        mega_service = MegaSyncService(db, mega_client)
                        stats["mega"] = mega_service.sync_all(
                            start_date=start_date,
                            end_date=end_date,
                            development_ids=empresa_ids,
                            sync_developments=True,
                            sync_contracts=True,
                            sync_financial=True,
                        )
                    logger.info(f"Mega sync completed: {stats['mega']}")
                except Exception as e:
                    logger.error(f"Mega sync failed: {e}", exc_info=True)
                    stats["mega"] = {"error": str(e)}

            # Sync UAU
            if origem in (SyncOrigin.UAU, SyncOrigin.BOTH):
                try:
                    logger.info("Starting UAU sync...")
                    with UAUAPIClient() as uau_client:
                        uau_service = UAUSyncService(db, uau_client)
                        stats["uau"] = uau_service.sync_all(
                            empresa_ids=empresa_ids,
                            start_date=start_date,
                            end_date=end_date,
                        )
                    logger.info(f"UAU sync completed: {stats['uau']}")
                except Exception as e:
                    logger.error(f"UAU sync failed: {e}", exc_info=True)
                    stats["uau"] = {"error": str(e)}

            # Check if any sync had errors
            has_error = (
                (stats.get("mega") and isinstance(stats["mega"], dict) and "error" in stats["mega"]) or
                (stats.get("uau") and isinstance(stats["uau"], dict) and "error" in stats["uau"])
            )

            # Update Run record
            run = db.query(Run).filter(Run.id == run_id).first()
            if run:
                run.status = "failed" if has_error else "success"
                run.finished_at = datetime.utcnow()
                run.metrics = stats
                db.commit()
                logger.info(f"Updated run record: ID={run_id}, status={run.status}")

        except Exception as e:
            # Update Run record with error
            run = db.query(Run).filter(Run.id == run_id).first()
            if run:
                run.status = "failed"
                run.finished_at = datetime.utcnow()
                run.error = str(e)
                db.commit()
            raise

    return stats


@router.post("/sync", response_model=SyncResponse)
def trigger_sync(
    request: SyncRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> SyncResponse:
    """
    Dispara sincronização com seleção de origem.

    - **origem**: mega, uau ou both
    - **start_date**: Data inicial (YYYY-MM-DD). Default: 12 meses atrás
    - **end_date**: Data final (YYYY-MM-DD). Default: hoje
    - **empresa_ids**: Lista de IDs específicos (opcional)

    A sincronização é executada em background.
    """
    # Parse dates
    start_date = None
    end_date = None

    if request.start_date:
        try:
            start_date = datetime.strptime(request.start_date, "%Y-%m-%d").date()
        except ValueError:
            raise HTTPException(status_code=400, detail="start_date deve estar no formato YYYY-MM-DD")

    if request.end_date:
        try:
            end_date = datetime.strptime(request.end_date, "%Y-%m-%d").date()
        except ValueError:
            raise HTTPException(status_code=400, detail="end_date deve estar no formato YYYY-MM-DD")

    logger.info(
        f"Sync triggered by {current_user.email} (id={current_user.id}): origem={request.origem}, "
        f"start={request.start_date}, end={request.end_date}, empresas={request.empresa_ids}"
    )

    # Add task to background
    background_tasks.add_task(
        _run_sync_task,
        origem=request.origem,
        start_date=start_date,
        end_date=end_date,
        empresa_ids=request.empresa_ids,
        user_id=current_user.id,
        user_email=current_user.email,
    )

    origem_label = {
        SyncOrigin.MEGA: "Mega",
        SyncOrigin.UAU: "UAU",
        SyncOrigin.BOTH: "Mega e UAU",
    }

    return SyncResponse(
        status="started",
        message=f"Sincronização {origem_label[request.origem]} iniciada em background",
        origem=request.origem.value,
    )


@router.get("/sync/origins")
def get_available_origins(
    current_user: User = Depends(get_current_active_user),
) -> dict:
    """
    Lista origens disponíveis para sincronização.
    """
    from starke.core.config import get_settings

    settings = get_settings()

    origins = []

    # Mega always available
    origins.append({
        "id": "mega",
        "name": "Mega ERP",
        "available": bool(settings.mega_api_url and settings.mega_api_username),
        "description": "Sistema Mega ERP",
    })

    # UAU available if configured
    origins.append({
        "id": "uau",
        "name": "UAU (Globaltec/Senior)",
        "available": bool(settings.uau_api_url and settings.uau_integration_token),
        "description": "Sistema UAU - Globaltec/Senior",
    })

    # Both option
    both_available = origins[0]["available"] and origins[1]["available"]
    origins.append({
        "id": "both",
        "name": "Ambos",
        "available": both_available,
        "description": "Sincronizar Mega e UAU simultaneamente",
    })

    return {"origins": origins}
