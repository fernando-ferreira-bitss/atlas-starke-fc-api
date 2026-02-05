"""Development routes for managing empreendimentos."""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from starke.api.dependencies import get_db
from starke.api.dependencies.auth import require_admin
from starke.infrastructure.database.models import Development, Filial, User

from .schemas import (
    DevelopmentActivateResponse,
    DevelopmentListResponse,
    DevelopmentResponse,
)

router = APIRouter(prefix="/developments", tags=["Developments"])


@router.get("", response_model=DevelopmentListResponse)
def list_developments(
    page: int = Query(1, ge=1, description="Página"),
    per_page: int = Query(20, ge=1, le=100, description="Itens por página"),
    is_active: Optional[bool] = Query(None, description="Filtrar por ativo/inativo"),
    origem: Optional[str] = Query(None, description="Filtrar por origem: mega ou uau"),
    search: Optional[str] = Query(None, description="Buscar por nome"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """List all developments with pagination and filters."""
    query = select(Development)

    # Apply filters
    if is_active is not None:
        query = query.where(Development.is_active == is_active)
    if origem:
        query = query.where(Development.origem == origem)
    if search:
        query = query.where(Development.name.ilike(f"%{search}%"))

    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total = db.execute(count_query).scalar() or 0

    # Pagination
    offset = (page - 1) * per_page
    query = query.order_by(Development.is_active.desc(), Development.name).offset(offset).limit(per_page)

    items = db.execute(query).scalars().all()

    return DevelopmentListResponse(
        items=[DevelopmentResponse.model_validate(item) for item in items],
        total=total,
        page=page,
        per_page=per_page,
        pages=(total + per_page - 1) // per_page if total > 0 else 0,
    )


@router.get("/{development_id}", response_model=DevelopmentResponse)
def get_development(
    development_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """Get development by ID."""
    development = db.get(Development, development_id)
    if not development:
        raise HTTPException(status_code=404, detail="Empreendimento não encontrado")
    return DevelopmentResponse.model_validate(development)


@router.patch("/{development_id}/activate", response_model=DevelopmentActivateResponse)
def activate_development(
    development_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """
    Activate a development for synchronization.

    Also activates the associated filial if it exists.
    """
    development = db.get(Development, development_id)
    if not development:
        raise HTTPException(status_code=404, detail="Empreendimento não encontrado")

    if development.is_active:
        raise HTTPException(
            status_code=400,
            detail=f"Empreendimento '{development.name}' já está ativo"
        )

    # Activate development
    development.is_active = True

    # Also activate associated filial
    filial_is_active = None
    if development.filial_id:
        filial = db.get(Filial, development.filial_id)
        if filial:
            filial.is_active = True
            filial_is_active = True

    db.commit()
    db.refresh(development)

    return DevelopmentActivateResponse(
        id=development.id,
        name=development.name,
        is_active=development.is_active,
        filial_id=development.filial_id,
        filial_is_active=filial_is_active,
        message=f"Empreendimento '{development.name}' ativado com sucesso",
    )


@router.patch("/{development_id}/deactivate", response_model=DevelopmentActivateResponse)
def deactivate_development(
    development_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """
    Deactivate a development from synchronization.

    Also deactivates the associated filial if it exists.
    """
    development = db.get(Development, development_id)
    if not development:
        raise HTTPException(status_code=404, detail="Empreendimento não encontrado")

    if not development.is_active:
        raise HTTPException(
            status_code=400,
            detail=f"Empreendimento '{development.name}' já está inativo"
        )

    # Deactivate development
    development.is_active = False

    # Also deactivate associated filial
    filial_is_active = None
    if development.filial_id:
        filial = db.get(Filial, development.filial_id)
        if filial:
            filial.is_active = False
            filial_is_active = False

    db.commit()
    db.refresh(development)

    return DevelopmentActivateResponse(
        id=development.id,
        name=development.name,
        is_active=development.is_active,
        filial_id=development.filial_id,
        filial_is_active=filial_is_active,
        message=f"Empreendimento '{development.name}' desativado com sucesso",
    )
