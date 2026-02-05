"""Audit log routes."""

from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select, and_, desc
from sqlalchemy.orm import Session

from starke.api.dependencies import get_current_active_user, get_db
from starke.infrastructure.database.models import User
from starke.infrastructure.database.patrimony.audit_log import PatAuditLog

from .schemas import (
    AuditLogResponse,
    AuditLogListResponse,
    AuditStatsResponse,
)

router = APIRouter(prefix="/audit", tags=["Audit Logs"])


def require_admin(current_user: User = Depends(get_current_active_user)) -> User:
    """Require admin role for audit access."""
    if current_user.role not in ("admin", "analyst"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Apenas administradores e analistas podem acessar logs de auditoria",
        )
    return current_user


@router.get("/logs", response_model=AuditLogListResponse)
def list_audit_logs(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
    page: int = Query(1, ge=1, description="Página"),
    per_page: int = Query(50, ge=1, le=100, description="Itens por página"),
    user_id: Optional[int] = Query(None, description="Filtrar por ID do usuário"),
    action: Optional[str] = Query(None, description="Filtrar por ação"),
    entity_type: Optional[str] = Query(None, description="Filtrar por tipo de entidade"),
    entity_id: Optional[str] = Query(None, description="Filtrar por ID da entidade"),
    ip_address: Optional[str] = Query(None, description="Filtrar por IP"),
    start_date: Optional[datetime] = Query(None, description="Data inicial"),
    end_date: Optional[datetime] = Query(None, description="Data final"),
) -> AuditLogListResponse:
    """Lista logs de auditoria com filtros e paginação.

    Apenas administradores e analistas podem acessar.
    """
    # Build query
    query = select(PatAuditLog)
    conditions = []

    if user_id is not None:
        conditions.append(PatAuditLog.user_id == user_id)
    if action:
        conditions.append(PatAuditLog.action == action)
    if entity_type:
        conditions.append(PatAuditLog.entity_type == entity_type)
    if entity_id:
        conditions.append(PatAuditLog.entity_id == entity_id)
    if ip_address:
        conditions.append(PatAuditLog.ip_address == ip_address)
    if start_date:
        conditions.append(PatAuditLog.created_at >= start_date)
    if end_date:
        conditions.append(PatAuditLog.created_at <= end_date)

    if conditions:
        query = query.where(and_(*conditions))

    # Count total
    count_query = select(func.count()).select_from(PatAuditLog)
    if conditions:
        count_query = count_query.where(and_(*conditions))
    total = db.execute(count_query).scalar() or 0

    # Apply pagination
    offset = (page - 1) * per_page
    query = query.order_by(desc(PatAuditLog.created_at)).offset(offset).limit(per_page)

    # Execute
    logs = db.execute(query).scalars().all()

    # Get user emails for logs
    user_ids = {log.user_id for log in logs if log.user_id}
    user_emails = {}
    if user_ids:
        users = db.execute(select(User).where(User.id.in_(user_ids))).scalars().all()
        user_emails = {u.id: u.email for u in users}

    # Build response
    items = []
    for log in logs:
        item = AuditLogResponse(
            id=log.id,
            user_id=log.user_id,
            user_email=user_emails.get(log.user_id) if log.user_id else None,
            action=log.action,
            entity_type=log.entity_type,
            entity_id=log.entity_id,
            ip_address=log.ip_address,
            user_agent=log.user_agent,
            details=log.details,
            created_at=log.created_at,
        )
        items.append(item)

    pages = (total + per_page - 1) // per_page

    return AuditLogListResponse(
        items=items,
        total=total,
        page=page,
        per_page=per_page,
        pages=pages,
    )


@router.get("/logs/{log_id}", response_model=AuditLogResponse)
def get_audit_log(
    log_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
) -> AuditLogResponse:
    """Busca um log de auditoria específico."""
    log = db.execute(
        select(PatAuditLog).where(PatAuditLog.id == log_id)
    ).scalar_one_or_none()

    if not log:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Log de auditoria não encontrado",
        )

    # Get user email
    user_email = None
    if log.user_id:
        user = db.execute(select(User).where(User.id == log.user_id)).scalar_one_or_none()
        if user:
            user_email = user.email

    return AuditLogResponse(
        id=log.id,
        user_id=log.user_id,
        user_email=user_email,
        action=log.action,
        entity_type=log.entity_type,
        entity_id=log.entity_id,
        ip_address=log.ip_address,
        user_agent=log.user_agent,
        details=log.details,
        created_at=log.created_at,
    )


@router.get("/stats", response_model=AuditStatsResponse)
def get_audit_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
    days: int = Query(30, ge=1, le=365, description="Número de dias para análise"),
) -> AuditStatsResponse:
    """Retorna estatísticas de auditoria dos últimos N dias.

    Apenas administradores e analistas podem acessar.
    """
    start_date = datetime.utcnow() - timedelta(days=days)

    # Total actions
    total_actions = db.execute(
        select(func.count())
        .select_from(PatAuditLog)
        .where(PatAuditLog.created_at >= start_date)
    ).scalar() or 0

    # Actions by type
    actions_result = db.execute(
        select(PatAuditLog.action, func.count())
        .where(PatAuditLog.created_at >= start_date)
        .group_by(PatAuditLog.action)
    ).all()
    actions_by_type = {row[0]: row[1] for row in actions_result}

    # Actions by entity type
    entity_result = db.execute(
        select(PatAuditLog.entity_type, func.count())
        .where(
            and_(
                PatAuditLog.created_at >= start_date,
                PatAuditLog.entity_type.isnot(None),
            )
        )
        .group_by(PatAuditLog.entity_type)
    ).all()
    actions_by_entity = {row[0]: row[1] for row in entity_result}

    # Top users by activity
    users_result = db.execute(
        select(PatAuditLog.user_id, func.count().label("count"))
        .where(
            and_(
                PatAuditLog.created_at >= start_date,
                PatAuditLog.user_id.isnot(None),
            )
        )
        .group_by(PatAuditLog.user_id)
        .order_by(desc("count"))
        .limit(10)
    ).all()

    # Get user emails for top users
    top_user_ids = [row[0] for row in users_result if row[0]]
    user_emails = {}
    if top_user_ids:
        users = db.execute(select(User).where(User.id.in_(top_user_ids))).scalars().all()
        user_emails = {u.id: u.email for u in users}

    top_users = [
        {
            "user_id": row[0],
            "email": user_emails.get(row[0], "Unknown"),
            "actions_count": row[1],
        }
        for row in users_result
        if row[0]
    ]

    # Recent logins
    recent_logins = db.execute(
        select(func.count())
        .select_from(PatAuditLog)
        .where(
            and_(
                PatAuditLog.created_at >= start_date,
                PatAuditLog.action == "login",
            )
        )
    ).scalar() or 0

    # Recent failed logins
    recent_failures = db.execute(
        select(func.count())
        .select_from(PatAuditLog)
        .where(
            and_(
                PatAuditLog.created_at >= start_date,
                PatAuditLog.action == "login_failed",
            )
        )
    ).scalar() or 0

    return AuditStatsResponse(
        total_actions=total_actions,
        actions_by_type=actions_by_type,
        actions_by_entity=actions_by_entity,
        top_users=top_users,
        recent_logins=recent_logins,
        recent_failures=recent_failures,
    )


@router.get("/entity/{entity_type}/{entity_id}", response_model=AuditLogListResponse)
def get_entity_audit_history(
    entity_type: str,
    entity_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=100),
) -> AuditLogListResponse:
    """Retorna histórico de auditoria de uma entidade específica.

    Útil para rastrear todas as ações realizadas em um cliente, ativo, etc.
    """
    query = select(PatAuditLog).where(
        and_(
            PatAuditLog.entity_type == entity_type,
            PatAuditLog.entity_id == entity_id,
        )
    )

    # Count total
    count_query = select(func.count()).select_from(PatAuditLog).where(
        and_(
            PatAuditLog.entity_type == entity_type,
            PatAuditLog.entity_id == entity_id,
        )
    )
    total = db.execute(count_query).scalar() or 0

    # Apply pagination
    offset = (page - 1) * per_page
    query = query.order_by(desc(PatAuditLog.created_at)).offset(offset).limit(per_page)

    # Execute
    logs = db.execute(query).scalars().all()

    # Get user emails
    user_ids = {log.user_id for log in logs if log.user_id}
    user_emails = {}
    if user_ids:
        users = db.execute(select(User).where(User.id.in_(user_ids))).scalars().all()
        user_emails = {u.id: u.email for u in users}

    # Build response
    items = []
    for log in logs:
        item = AuditLogResponse(
            id=log.id,
            user_id=log.user_id,
            user_email=user_emails.get(log.user_id) if log.user_id else None,
            action=log.action,
            entity_type=log.entity_type,
            entity_id=log.entity_id,
            ip_address=log.ip_address,
            user_agent=log.user_agent,
            details=log.details,
            created_at=log.created_at,
        )
        items.append(item)

    pages = (total + per_page - 1) // per_page

    return AuditLogListResponse(
        items=items,
        total=total,
        page=page,
        per_page=per_page,
        pages=pages,
    )


@router.get("/user/{user_id}/activity", response_model=AuditLogListResponse)
def get_user_activity(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=100),
    days: int = Query(30, ge=1, le=365, description="Últimos N dias"),
) -> AuditLogListResponse:
    """Retorna atividade de um usuário específico.

    Útil para monitorar ações de um usuário.
    """
    start_date = datetime.utcnow() - timedelta(days=days)

    query = select(PatAuditLog).where(
        and_(
            PatAuditLog.user_id == user_id,
            PatAuditLog.created_at >= start_date,
        )
    )

    # Count total
    count_query = select(func.count()).select_from(PatAuditLog).where(
        and_(
            PatAuditLog.user_id == user_id,
            PatAuditLog.created_at >= start_date,
        )
    )
    total = db.execute(count_query).scalar() or 0

    # Apply pagination
    offset = (page - 1) * per_page
    query = query.order_by(desc(PatAuditLog.created_at)).offset(offset).limit(per_page)

    # Execute
    logs = db.execute(query).scalars().all()

    # Get user email
    user = db.execute(select(User).where(User.id == user_id)).scalar_one_or_none()
    user_email = user.email if user else None

    # Build response
    items = [
        AuditLogResponse(
            id=log.id,
            user_id=log.user_id,
            user_email=user_email,
            action=log.action,
            entity_type=log.entity_type,
            entity_id=log.entity_id,
            ip_address=log.ip_address,
            user_agent=log.user_agent,
            details=log.details,
            created_at=log.created_at,
        )
        for log in logs
    ]

    pages = (total + per_page - 1) // per_page

    return AuditLogListResponse(
        items=items,
        total=total,
        page=page,
        per_page=per_page,
        pages=pages,
    )
