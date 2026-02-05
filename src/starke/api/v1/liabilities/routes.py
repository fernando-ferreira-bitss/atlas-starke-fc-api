"""Liability routes."""

from decimal import Decimal
from typing import Optional
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select, or_
from sqlalchemy.orm import Session, joinedload, contains_eager

from starke.api.dependencies import get_db
from starke.api.dependencies.auth import require_permission
from starke.domain.permissions.screens import Screen
from starke.infrastructure.database.models import User, UserRole
from starke.infrastructure.database.patrimony.liability import PatLiability
from starke.infrastructure.database.patrimony.institution import PatInstitution
from starke.infrastructure.database.patrimony.client import PatClient
from starke.infrastructure.database.patrimony.document import PatDocument

from .schemas import (
    DocumentSummary,
    InstitutionSummary,
    LiabilitiesByType,
    LiabilityCreate,
    LiabilityListResponse,
    LiabilityResponse,
    LiabilityUpdate,
)

router = APIRouter(prefix="/liabilities", tags=["Liabilities"])


def check_client_access(client_id: str, current_user: User, db: Session) -> PatClient:
    """Check if user has access to client and return client."""
    query = select(PatClient).where(PatClient.id == client_id)

    if current_user.role == UserRole.CLIENT.value:
        query = query.where(PatClient.user_id == current_user.id)
    elif current_user.role == UserRole.RM.value:
        query = query.where(PatClient.rm_user_id == current_user.id)

    client = db.execute(query).scalar_one_or_none()
    if not client:
        raise HTTPException(status_code=404, detail="Cliente não encontrado")
    return client


def build_liability_response(liability: PatLiability) -> LiabilityResponse:
    """Build liability response with computed fields."""
    institution = None
    if liability.institution:
        institution = InstitutionSummary(
            id=liability.institution.id,
            name=liability.institution.name,
            code=liability.institution.code,
        )

    # Calculate remaining payments
    remaining_payments = None
    total_to_pay = None
    if liability.monthly_payment and liability.monthly_payment > 0:
        remaining_payments = int(
            liability.current_balance / liability.monthly_payment
        ) + 1
        total_to_pay = liability.current_balance

    # Build documents list
    documents = []
    for doc in liability.documents:
        documents.append(DocumentSummary(
            id=doc.id,
            title=doc.title,
            document_type=doc.document_type,
            file_name=doc.file_name,
            created_at=doc.created_at,
        ))

    return LiabilityResponse(
        id=liability.id,
        client_id=liability.client_id,
        institution_id=liability.institution_id,
        institution=institution,
        liability_type=liability.liability_type,
        description=liability.description,
        notes=liability.notes,
        original_amount=liability.original_amount,
        current_balance=liability.current_balance,
        monthly_payment=liability.monthly_payment,
        interest_rate=liability.interest_rate,
        start_date=liability.start_date,
        end_date=liability.end_date,
        last_payment_date=liability.last_payment_date,
        currency=liability.currency,
        is_active=liability.is_active,
        is_paid_off=liability.is_paid_off,
        created_at=liability.created_at,
        updated_at=liability.updated_at,
        remaining_payments=remaining_payments,
        total_to_pay=total_to_pay,
        documents=documents,
    )


@router.get("", response_model=LiabilityListResponse)
def list_liabilities(
    page: int = Query(1, ge=1, description="Página"),
    per_page: int = Query(20, ge=1, le=100, description="Itens por página"),
    client_id: Optional[str] = Query(None, description="Filtrar por cliente"),
    institution_id: Optional[str] = Query(None, description="Filtrar por instituição"),
    liability_type: Optional[str] = Query(None, description="Filtrar por tipo"),
    is_active: Optional[bool] = Query(None, description="Filtrar por ativo/inativo"),
    search: Optional[str] = Query(None, description="Buscar por descrição ou nome do cliente"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Screen.LIABILITIES)),
):
    """List liabilities with pagination and access control."""
    # Build base query with join for search capability
    query = (
        select(PatLiability)
        .join(PatClient, PatLiability.client_id == PatClient.id)
        .options(
            contains_eager(PatLiability.client),
            joinedload(PatLiability.institution),
        )
    )

    # Access control
    if current_user.role == UserRole.CLIENT.value:
        client = db.execute(
            select(PatClient).where(PatClient.user_id == current_user.id)
        ).scalar_one_or_none()
        if client:
            query = query.where(PatLiability.client_id == client.id)
        else:
            query = query.where(False)
    elif current_user.role == UserRole.RM.value:
        client_ids = db.execute(
            select(PatClient.id).where(PatClient.rm_user_id == current_user.id)
        ).scalars().all()
        query = query.where(PatLiability.client_id.in_(client_ids))

    # Apply filters
    if client_id:
        query = query.where(PatLiability.client_id == client_id)
    if institution_id:
        query = query.where(PatLiability.institution_id == institution_id)
    if liability_type:
        query = query.where(PatLiability.liability_type == liability_type)
    if is_active is not None:
        query = query.where(PatLiability.is_active == is_active)
    if search:
        search_filter = f"%{search}%"
        query = query.where(
            or_(PatLiability.description.ilike(search_filter), PatClient.name.ilike(search_filter))
        )

    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total = db.execute(count_query).scalar() or 0

    # Pagination
    offset = (page - 1) * per_page
    query = query.order_by(PatLiability.current_balance.desc()).offset(offset).limit(per_page)

    items = db.execute(query).unique().scalars().all()

    return LiabilityListResponse(
        items=[build_liability_response(item) for item in items],
        total=total,
        page=page,
        per_page=per_page,
        pages=(total + per_page - 1) // per_page if total > 0 else 0,
    )


@router.get("/by-client/{client_id}", response_model=list[LiabilityResponse])
def get_liabilities_by_client(
    client_id: str,
    liability_type: Optional[str] = Query(None, description="Filtrar por tipo"),
    is_active: Optional[bool] = Query(True, description="Filtrar por ativo/inativo"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Screen.LIABILITIES)),
):
    """Get all liabilities for a client."""
    check_client_access(client_id, current_user, db)

    query = (
        select(PatLiability)
        .options(joinedload(PatLiability.institution))
        .where(PatLiability.client_id == client_id)
    )
    if liability_type:
        query = query.where(PatLiability.liability_type == liability_type)
    if is_active is not None:
        query = query.where(PatLiability.is_active == is_active)

    liabilities = db.execute(query).unique().scalars().all()
    return [build_liability_response(l) for l in liabilities]


@router.get("/by-client/{client_id}/grouped", response_model=list[LiabilitiesByType])
def get_liabilities_grouped_by_type(
    client_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Screen.LIABILITIES)),
):
    """Get liabilities grouped by type for a client."""
    check_client_access(client_id, current_user, db)

    # Get totals by type
    totals = db.execute(
        select(
            PatLiability.liability_type,
            func.sum(PatLiability.current_balance).label("total_balance"),
            func.sum(PatLiability.monthly_payment).label("total_monthly"),
            func.count().label("count"),
        )
        .where(PatLiability.client_id == client_id)
        .where(PatLiability.is_active == True)
        .group_by(PatLiability.liability_type)
    ).all()

    # Calculate grand total for percentages
    grand_total = sum(t.total_balance or Decimal("0") for t in totals)

    # Get liabilities grouped
    result = []
    for total_row in totals:
        liabilities = db.execute(
            select(PatLiability)
            .options(joinedload(PatLiability.institution))
            .where(PatLiability.client_id == client_id)
            .where(PatLiability.liability_type == total_row.liability_type)
            .where(PatLiability.is_active == True)
        ).unique().scalars().all()

        percentage = 0.0
        if grand_total > 0:
            percentage = float(
                (total_row.total_balance or Decimal("0")) / grand_total * 100
            )

        result.append(
            LiabilitiesByType(
                liability_type=total_row.liability_type,
                total_balance=total_row.total_balance or Decimal("0"),
                total_monthly_payment=total_row.total_monthly or Decimal("0"),
                count=total_row.count,
                percentage=percentage,
                liabilities=[build_liability_response(l) for l in liabilities],
            )
        )

    return result


@router.get("/{liability_id}", response_model=LiabilityResponse)
def get_liability(
    liability_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Screen.LIABILITIES)),
):
    """Get liability by ID."""
    liability = db.execute(
        select(PatLiability)
        .options(joinedload(PatLiability.institution))
        .where(PatLiability.id == liability_id)
    ).unique().scalar_one_or_none()

    if not liability:
        raise HTTPException(status_code=404, detail="Passivo não encontrado")

    check_client_access(liability.client_id, current_user, db)

    return build_liability_response(liability)


@router.post("", response_model=LiabilityResponse, status_code=201)
def create_liability(
    data: LiabilityCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Screen.LIABILITIES)),
):
    """Create a new liability."""
    check_client_access(data.client_id, current_user, db)

    # Validate institution if provided
    if data.institution_id:
        institution = db.get(PatInstitution, data.institution_id)
        if not institution:
            raise HTTPException(status_code=400, detail="Instituição não encontrada")

    liability = PatLiability(
        id=str(uuid4()),
        client_id=data.client_id,
        institution_id=data.institution_id,
        liability_type=data.liability_type,
        description=data.description,
        notes=data.notes,
        original_amount=data.original_amount,
        current_balance=data.current_balance,
        monthly_payment=data.monthly_payment,
        interest_rate=data.interest_rate,
        start_date=data.start_date,
        end_date=data.end_date,
        last_payment_date=data.last_payment_date,
        currency=data.currency,
        is_active=True,
    )
    db.add(liability)
    db.flush()  # Get the liability ID

    # Link documents if provided
    if data.document_ids:
        for doc_id in data.document_ids:
            doc = db.get(PatDocument, doc_id)
            if doc and doc.client_id == data.client_id:
                doc.liability_id = liability.id

    db.commit()

    # Reload with institution
    liability = db.execute(
        select(PatLiability)
        .options(joinedload(PatLiability.institution))
        .where(PatLiability.id == liability.id)
    ).unique().scalar_one()

    return build_liability_response(liability)


@router.put("/{liability_id}", response_model=LiabilityResponse)
def update_liability(
    liability_id: str,
    data: LiabilityUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Screen.LIABILITIES)),
):
    """Update a liability."""
    liability = db.get(PatLiability, liability_id)
    if not liability:
        raise HTTPException(status_code=404, detail="Passivo não encontrado")

    check_client_access(liability.client_id, current_user, db)

    # Validate institution if provided
    if data.institution_id:
        institution = db.get(PatInstitution, data.institution_id)
        if not institution:
            raise HTTPException(status_code=400, detail="Instituição não encontrada")

    # Update only provided fields (exclude document_ids from direct update)
    update_data = data.model_dump(exclude_unset=True, exclude={"document_ids"})
    for field, value in update_data.items():
        setattr(liability, field, value)

    # Add document links if provided (does not remove existing)
    if data.document_ids:
        for doc_id in data.document_ids:
            doc = db.get(PatDocument, doc_id)
            if doc and doc.client_id == liability.client_id:
                doc.liability_id = liability.id

    db.commit()

    # Reload with institution
    liability = db.execute(
        select(PatLiability)
        .options(joinedload(PatLiability.institution))
        .where(PatLiability.id == liability.id)
    ).unique().scalar_one()

    return build_liability_response(liability)


@router.delete("/{liability_id}", status_code=204)
def delete_liability(
    liability_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Screen.LIABILITIES)),
):
    """Delete a liability (soft delete)."""
    liability = db.get(PatLiability, liability_id)
    if not liability:
        raise HTTPException(status_code=404, detail="Passivo não encontrado")

    check_client_access(liability.client_id, current_user, db)

    # Soft delete
    liability.is_active = False
    db.commit()
    return None
