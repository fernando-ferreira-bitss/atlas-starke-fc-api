"""Account routes."""

from typing import Optional
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

from starke.api.dependencies import get_db
from starke.api.dependencies.auth import require_permission
from starke.domain.permissions.screens import Screen
from starke.infrastructure.database.models import User, UserRole
from starke.infrastructure.database.patrimony.account import PatAccount
from starke.infrastructure.database.patrimony.client import PatClient
from starke.infrastructure.database.patrimony.institution import PatInstitution

from .schemas import (
    AccountCreate,
    AccountListResponse,
    AccountResponse,
    AccountUpdate,
    ClientSummary,
    InstitutionSummary,
)

router = APIRouter(prefix="/accounts", tags=["Accounts"])


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


def build_account_response(account: PatAccount) -> AccountResponse:
    """Build account response with client and institution info."""
    client = None
    if account.client:
        client = ClientSummary(
            id=account.client.id,
            name=account.client.name,
            client_type=account.client.client_type,
        )

    institution = None
    if account.institution:
        institution = InstitutionSummary(
            id=account.institution.id,
            name=account.institution.name,
            code=account.institution.code,
        )

    return AccountResponse(
        id=account.id,
        client_id=account.client_id,
        client=client,
        institution_id=account.institution_id,
        institution=institution,
        account_type=account.account_type,
        account_number=account.account_number,
        agency=account.agency,
        currency=account.currency,
        base_date=account.base_date,
        notes=account.notes,
        is_active=account.is_active,
        created_at=account.created_at,
        updated_at=account.updated_at,
    )


@router.get("", response_model=AccountListResponse)
def list_accounts(
    page: int = Query(1, ge=1, description="Página"),
    per_page: int = Query(20, ge=1, le=100, description="Itens por página"),
    client_id: Optional[str] = Query(None, description="Filtrar por cliente"),
    institution_id: Optional[str] = Query(None, description="Filtrar por instituição"),
    account_type: Optional[str] = Query(None, description="Filtrar por tipo"),
    is_active: Optional[bool] = Query(None, description="Filtrar por ativo/inativo"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Screen.ACCOUNTS)),
):
    """List accounts with pagination and access control."""
    query = select(PatAccount).options(
        joinedload(PatAccount.institution),
        joinedload(PatAccount.client),
    )

    # Access control
    if current_user.role == UserRole.CLIENT.value:
        client = db.execute(
            select(PatClient).where(PatClient.user_id == current_user.id)
        ).scalar_one_or_none()
        if client:
            query = query.where(PatAccount.client_id == client.id)
        else:
            query = query.where(False)
    elif current_user.role == UserRole.RM.value:
        client_ids = db.execute(
            select(PatClient.id).where(PatClient.rm_user_id == current_user.id)
        ).scalars().all()
        query = query.where(PatAccount.client_id.in_(client_ids))

    # Apply filters
    if client_id:
        query = query.where(PatAccount.client_id == client_id)
    if institution_id:
        query = query.where(PatAccount.institution_id == institution_id)
    if account_type:
        query = query.where(PatAccount.account_type == account_type)
    if is_active is not None:
        query = query.where(PatAccount.is_active == is_active)

    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total = db.execute(count_query).scalar() or 0

    # Pagination
    offset = (page - 1) * per_page
    query = query.order_by(PatAccount.created_at.desc()).offset(offset).limit(per_page)

    items = db.execute(query).unique().scalars().all()

    return AccountListResponse(
        items=[build_account_response(item) for item in items],
        total=total,
        page=page,
        per_page=per_page,
        pages=(total + per_page - 1) // per_page if total > 0 else 0,
    )


@router.get("/by-client/{client_id}", response_model=list[AccountResponse])
def get_accounts_by_client(
    client_id: str,
    is_active: Optional[bool] = Query(True, description="Filtrar por ativo/inativo"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Screen.ACCOUNTS)),
):
    """Get all accounts for a client."""
    # Check access to client
    check_client_access(client_id, current_user, db)

    query = (
        select(PatAccount)
        .options(
            joinedload(PatAccount.institution),
            joinedload(PatAccount.client),
        )
        .where(PatAccount.client_id == client_id)
    )
    if is_active is not None:
        query = query.where(PatAccount.is_active == is_active)

    accounts = db.execute(query).unique().scalars().all()
    return [build_account_response(acc) for acc in accounts]


@router.get("/{account_id}", response_model=AccountResponse)
def get_account(
    account_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Screen.ACCOUNTS)),
):
    """Get account by ID."""
    account = db.execute(
        select(PatAccount)
        .options(
            joinedload(PatAccount.institution),
            joinedload(PatAccount.client),
        )
        .where(PatAccount.id == account_id)
    ).unique().scalar_one_or_none()

    if not account:
        raise HTTPException(status_code=404, detail="Conta não encontrada")

    # Check access to client
    check_client_access(account.client_id, current_user, db)

    return build_account_response(account)


@router.post("", response_model=AccountResponse, status_code=201)
def create_account(
    data: AccountCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Screen.ACCOUNTS)),
):
    """Create a new account."""
    # Check access to client
    check_client_access(data.client_id, current_user, db)

    # Validate institution if provided
    if data.institution_id:
        institution = db.get(PatInstitution, data.institution_id)
        if not institution:
            raise HTTPException(status_code=400, detail="Instituição não encontrada")

    account = PatAccount(
        id=str(uuid4()),
        client_id=data.client_id,
        institution_id=data.institution_id,
        account_type=data.account_type,
        account_number=data.account_number,
        agency=data.agency,
        currency=data.currency,
        base_date=data.base_date,
        notes=data.notes,
        is_active=True,
    )
    db.add(account)
    db.commit()

    # Reload with relationships
    account = db.execute(
        select(PatAccount)
        .options(
            joinedload(PatAccount.institution),
            joinedload(PatAccount.client),
        )
        .where(PatAccount.id == account.id)
    ).unique().scalar_one()

    return build_account_response(account)


@router.put("/{account_id}", response_model=AccountResponse)
def update_account(
    account_id: str,
    data: AccountUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Screen.ACCOUNTS)),
):
    """Update an account."""
    account = db.get(PatAccount, account_id)
    if not account:
        raise HTTPException(status_code=404, detail="Conta não encontrada")

    # Check access to client
    check_client_access(account.client_id, current_user, db)

    # Validate institution if provided
    if data.institution_id:
        institution = db.get(PatInstitution, data.institution_id)
        if not institution:
            raise HTTPException(status_code=400, detail="Instituição não encontrada")

    # Update only provided fields
    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(account, field, value)

    db.commit()

    # Reload with relationships
    account = db.execute(
        select(PatAccount)
        .options(
            joinedload(PatAccount.institution),
            joinedload(PatAccount.client),
        )
        .where(PatAccount.id == account.id)
    ).unique().scalar_one()

    return build_account_response(account)


@router.delete("/{account_id}", status_code=204)
def delete_account(
    account_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Screen.ACCOUNTS)),
):
    """Delete an account (soft delete)."""
    account = db.get(PatAccount, account_id)
    if not account:
        raise HTTPException(status_code=404, detail="Conta não encontrada")

    # Check access to client
    check_client_access(account.client_id, current_user, db)

    # Soft delete
    account.is_active = False
    db.commit()
    return None
