"""Institution routes."""

from typing import Optional
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from starke.api.dependencies import get_db
from starke.api.dependencies.auth import get_current_user, require_permission
from starke.domain.permissions.screens import Screen
from starke.infrastructure.database.models import User
from starke.infrastructure.database.patrimony.institution import PatInstitution

from .schemas import (
    InstitutionCreate,
    InstitutionListResponse,
    InstitutionResponse,
    InstitutionUpdate,
)

router = APIRouter(prefix="/institutions", tags=["Institutions"])


@router.get("", response_model=InstitutionListResponse)
def list_institutions(
    page: int = Query(1, ge=1, description="Página"),
    per_page: int = Query(20, ge=1, le=100, description="Itens por página"),
    is_active: Optional[bool] = Query(None, description="Filtrar por ativo/inativo"),
    institution_type: Optional[str] = Query(None, description="Filtrar por tipo"),
    search: Optional[str] = Query(None, description="Buscar por nome"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Screen.INSTITUTIONS)),
):
    """List all institutions with pagination."""
    query = select(PatInstitution)

    # Apply filters
    if is_active is not None:
        query = query.where(PatInstitution.is_active == is_active)
    if institution_type:
        query = query.where(PatInstitution.institution_type == institution_type)
    if search:
        query = query.where(PatInstitution.name.ilike(f"%{search}%"))

    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total = db.execute(count_query).scalar() or 0

    # Pagination
    offset = (page - 1) * per_page
    query = query.order_by(PatInstitution.name).offset(offset).limit(per_page)

    items = db.execute(query).scalars().all()

    return InstitutionListResponse(
        items=[InstitutionResponse.model_validate(item) for item in items],
        total=total,
        page=page,
        per_page=per_page,
        pages=(total + per_page - 1) // per_page if total > 0 else 0,
    )


@router.get("/{institution_id}", response_model=InstitutionResponse)
def get_institution(
    institution_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Screen.INSTITUTIONS)),
):
    """Get institution by ID."""
    institution = db.get(PatInstitution, institution_id)
    if not institution:
        raise HTTPException(status_code=404, detail="Instituição não encontrada")
    return InstitutionResponse.model_validate(institution)


@router.post("", response_model=InstitutionResponse, status_code=201)
def create_institution(
    data: InstitutionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Screen.INSTITUTIONS)),
):
    """Create a new institution."""
    # Check if code already exists
    existing = db.execute(
        select(PatInstitution).where(PatInstitution.code == data.code)
    ).scalar_one_or_none()
    if existing:
        raise HTTPException(
            status_code=400,
            detail=f"Já existe uma instituição com o código '{data.code}'"
        )

    # Check if name already exists
    existing_name = db.execute(
        select(PatInstitution).where(PatInstitution.name == data.name)
    ).scalar_one_or_none()
    if existing_name:
        raise HTTPException(
            status_code=400,
            detail=f"Já existe uma instituição com o nome '{data.name}'"
        )

    institution = PatInstitution(
        id=str(uuid4()),
        name=data.name,
        code=data.code,
        institution_type=data.institution_type,
        is_active=True,
    )
    db.add(institution)
    db.commit()
    db.refresh(institution)
    return InstitutionResponse.model_validate(institution)


@router.put("/{institution_id}", response_model=InstitutionResponse)
def update_institution(
    institution_id: str,
    data: InstitutionUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Screen.INSTITUTIONS)),
):
    """Update an institution."""
    institution = db.get(PatInstitution, institution_id)
    if not institution:
        raise HTTPException(status_code=404, detail="Instituição não encontrada")

    # Check if new code already exists in another institution
    if data.code and data.code != institution.code:
        existing = db.execute(
            select(PatInstitution).where(
                PatInstitution.code == data.code,
                PatInstitution.id != institution_id
            )
        ).scalar_one_or_none()
        if existing:
            raise HTTPException(
                status_code=400,
                detail=f"Já existe uma instituição com o código '{data.code}'"
            )

    # Check if new name already exists in another institution
    if data.name and data.name != institution.name:
        existing_name = db.execute(
            select(PatInstitution).where(
                PatInstitution.name == data.name,
                PatInstitution.id != institution_id
            )
        ).scalar_one_or_none()
        if existing_name:
            raise HTTPException(
                status_code=400,
                detail=f"Já existe uma instituição com o nome '{data.name}'"
            )

    # Update only provided fields
    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(institution, field, value)

    db.commit()
    db.refresh(institution)
    return InstitutionResponse.model_validate(institution)


@router.delete("/{institution_id}", status_code=204)
def delete_institution(
    institution_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Screen.INSTITUTIONS)),
):
    """Delete an institution (soft delete - sets is_active=False)."""
    institution = db.get(PatInstitution, institution_id)
    if not institution:
        raise HTTPException(status_code=404, detail="Instituição não encontrada")

    # Soft delete
    institution.is_active = False
    db.commit()
    return None
