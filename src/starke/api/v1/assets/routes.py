"""Asset routes."""

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
from starke.infrastructure.database.patrimony.asset import PatAsset
from starke.infrastructure.database.patrimony.account import PatAccount
from starke.infrastructure.database.patrimony.client import PatClient
from starke.infrastructure.database.patrimony.document import PatDocument

from .schemas import (
    AccountSummary,
    AssetCreate,
    AssetListResponse,
    AssetResponse,
    AssetsByCategory,
    AssetUpdate,
    ClientSummary,
    DocumentSummary,
)

router = APIRouter(prefix="/assets", tags=["Assets"])


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


def build_asset_response(asset: PatAsset) -> AssetResponse:
    """Build asset response with computed fields."""
    client = None
    if asset.client:
        client = ClientSummary(
            id=asset.client.id,
            name=asset.client.name,
            client_type=asset.client.client_type,
        )

    account = None
    if asset.account:
        institution_name = None
        if asset.account.institution:
            institution_name = asset.account.institution.name
        account = AccountSummary(
            id=asset.account.id,
            account_type=asset.account.account_type,
            institution_name=institution_name,
        )

    # Calculate gain/loss
    gain_loss = None
    gain_loss_percent = None
    if asset.base_value and asset.current_value and asset.base_value > 0:
        gain_loss = asset.current_value - asset.base_value
        gain_loss_percent = float(
            (asset.current_value - asset.base_value) / asset.base_value * 100
        )

    # Build documents list
    documents = []
    for doc in asset.documents:
        documents.append(DocumentSummary(
            id=doc.id,
            title=doc.title,
            document_type=doc.document_type,
            file_name=doc.file_name,
            created_at=doc.created_at,
        ))

    return AssetResponse(
        id=asset.id,
        client_id=asset.client_id,
        client=client,
        account_id=asset.account_id,
        account=account,
        category=asset.category,
        subcategory=asset.subcategory,
        name=asset.name,
        description=asset.description,
        ticker=asset.ticker,
        base_value=asset.base_value,
        current_value=asset.current_value,
        quantity=asset.quantity,
        base_date=asset.base_date,
        base_year=asset.base_year,
        maturity_date=asset.maturity_date,
        currency=asset.currency,
        is_active=asset.is_active,
        created_at=asset.created_at,
        updated_at=asset.updated_at,
        gain_loss=gain_loss,
        gain_loss_percent=gain_loss_percent,
        documents=documents,
    )


@router.get("", response_model=AssetListResponse)
def list_assets(
    page: int = Query(1, ge=1, description="Página"),
    per_page: int = Query(20, ge=1, le=100, description="Itens por página"),
    client_id: Optional[str] = Query(None, description="Filtrar por cliente"),
    account_id: Optional[str] = Query(None, description="Filtrar por conta"),
    category: Optional[str] = Query(None, description="Filtrar por categoria"),
    is_active: Optional[bool] = Query(None, description="Filtrar por ativo/inativo"),
    search: Optional[str] = Query(None, description="Buscar por nome do ativo ou nome do cliente"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Screen.ASSETS)),
):
    """List assets with pagination and access control."""
    # Build base query with join for search capability
    query = (
        select(PatAsset)
        .join(PatClient, PatAsset.client_id == PatClient.id)
        .options(
            contains_eager(PatAsset.client),
            joinedload(PatAsset.account).joinedload(PatAccount.institution),
        )
    )

    # Access control
    if current_user.role == UserRole.CLIENT.value:
        client = db.execute(
            select(PatClient).where(PatClient.user_id == current_user.id)
        ).scalar_one_or_none()
        if client:
            query = query.where(PatAsset.client_id == client.id)
        else:
            query = query.where(False)
    elif current_user.role == UserRole.RM.value:
        client_ids = db.execute(
            select(PatClient.id).where(PatClient.rm_user_id == current_user.id)
        ).scalars().all()
        query = query.where(PatAsset.client_id.in_(client_ids))

    # Apply filters
    if client_id:
        query = query.where(PatAsset.client_id == client_id)
    if account_id:
        query = query.where(PatAsset.account_id == account_id)
    if category:
        query = query.where(PatAsset.category == category)
    if is_active is not None:
        query = query.where(PatAsset.is_active == is_active)
    if search:
        search_filter = f"%{search}%"
        query = query.where(
            or_(PatAsset.name.ilike(search_filter), PatClient.name.ilike(search_filter))
        )

    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total = db.execute(count_query).scalar() or 0

    # Pagination
    offset = (page - 1) * per_page
    query = query.order_by(PatAsset.name).offset(offset).limit(per_page)

    items = db.execute(query).unique().scalars().all()

    return AssetListResponse(
        items=[build_asset_response(item) for item in items],
        total=total,
        page=page,
        per_page=per_page,
        pages=(total + per_page - 1) // per_page if total > 0 else 0,
    )


@router.get("/by-client/{client_id}", response_model=list[AssetResponse])
def get_assets_by_client(
    client_id: str,
    category: Optional[str] = Query(None, description="Filtrar por categoria"),
    is_active: Optional[bool] = Query(True, description="Filtrar por ativo/inativo"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Screen.ASSETS)),
):
    """Get all assets for a client."""
    check_client_access(client_id, current_user, db)

    query = (
        select(PatAsset)
        .options(
            joinedload(PatAsset.client),
            joinedload(PatAsset.account).joinedload(PatAccount.institution),
        )
        .where(PatAsset.client_id == client_id)
    )
    if category:
        query = query.where(PatAsset.category == category)
    if is_active is not None:
        query = query.where(PatAsset.is_active == is_active)

    assets = db.execute(query).unique().scalars().all()
    return [build_asset_response(a) for a in assets]


@router.get("/by-client/{client_id}/grouped", response_model=list[AssetsByCategory])
def get_assets_grouped_by_category(
    client_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Screen.ASSETS)),
):
    """Get assets grouped by category for a client."""
    check_client_access(client_id, current_user, db)

    # Get totals by category
    totals = db.execute(
        select(
            PatAsset.category,
            func.sum(PatAsset.current_value).label("total"),
            func.count().label("count"),
        )
        .where(PatAsset.client_id == client_id)
        .where(PatAsset.is_active == True)
        .group_by(PatAsset.category)
    ).all()

    # Calculate grand total for percentages
    grand_total = sum(t.total or Decimal("0") for t in totals)

    # Get assets grouped
    result = []
    for total_row in totals:
        assets = db.execute(
            select(PatAsset)
            .options(
                joinedload(PatAsset.client),
                joinedload(PatAsset.account).joinedload(PatAccount.institution),
            )
            .where(PatAsset.client_id == client_id)
            .where(PatAsset.category == total_row.category)
            .where(PatAsset.is_active == True)
        ).unique().scalars().all()

        percentage = 0.0
        if grand_total > 0:
            percentage = float((total_row.total or Decimal("0")) / grand_total * 100)

        result.append(
            AssetsByCategory(
                category=total_row.category,
                total_value=total_row.total or Decimal("0"),
                count=total_row.count,
                percentage=percentage,
                assets=[build_asset_response(a) for a in assets],
            )
        )

    return result


@router.get("/{asset_id}", response_model=AssetResponse)
def get_asset(
    asset_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Screen.ASSETS)),
):
    """Get asset by ID."""
    asset = db.execute(
        select(PatAsset)
        .options(
            joinedload(PatAsset.client),
            joinedload(PatAsset.account).joinedload(PatAccount.institution),
        )
        .where(PatAsset.id == asset_id)
    ).unique().scalar_one_or_none()

    if not asset:
        raise HTTPException(status_code=404, detail="Ativo não encontrado")

    check_client_access(asset.client_id, current_user, db)

    return build_asset_response(asset)


@router.post("", response_model=AssetResponse, status_code=201)
def create_asset(
    data: AssetCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Screen.ASSETS)),
):
    """Create a new asset."""
    check_client_access(data.client_id, current_user, db)

    # Validate account if provided
    if data.account_id:
        account = db.get(PatAccount, data.account_id)
        if not account or account.client_id != data.client_id:
            raise HTTPException(status_code=400, detail="Conta não encontrada")

    asset = PatAsset(
        id=str(uuid4()),
        client_id=data.client_id,
        account_id=data.account_id,
        category=data.category,
        subcategory=data.subcategory,
        name=data.name,
        description=data.description,
        ticker=data.ticker,
        base_value=data.base_value,
        current_value=data.current_value,
        quantity=data.quantity,
        base_date=data.base_date,
        base_year=data.base_year,
        maturity_date=data.maturity_date,
        currency=data.currency,
        is_active=True,
    )
    db.add(asset)
    db.flush()  # Get the asset ID

    # Link documents if provided
    if data.document_ids:
        for doc_id in data.document_ids:
            doc = db.get(PatDocument, doc_id)
            if doc and doc.client_id == data.client_id:
                doc.asset_id = asset.id

    db.commit()

    # Reload with relationships
    asset = db.execute(
        select(PatAsset)
        .options(
            joinedload(PatAsset.client),
            joinedload(PatAsset.account).joinedload(PatAccount.institution),
        )
        .where(PatAsset.id == asset.id)
    ).unique().scalar_one()

    return build_asset_response(asset)


@router.put("/{asset_id}", response_model=AssetResponse)
def update_asset(
    asset_id: str,
    data: AssetUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Screen.ASSETS)),
):
    """Update an asset."""
    asset = db.get(PatAsset, asset_id)
    if not asset:
        raise HTTPException(status_code=404, detail="Ativo não encontrado")

    check_client_access(asset.client_id, current_user, db)

    # Validate account if provided
    if data.account_id:
        account = db.get(PatAccount, data.account_id)
        if not account or account.client_id != asset.client_id:
            raise HTTPException(status_code=400, detail="Conta não encontrada")

    # Update only provided fields (exclude document_ids from direct update)
    update_data = data.model_dump(exclude_unset=True, exclude={"document_ids"})
    for field, value in update_data.items():
        setattr(asset, field, value)

    # Add document links if provided (does not remove existing)
    if data.document_ids:
        for doc_id in data.document_ids:
            doc = db.get(PatDocument, doc_id)
            if doc and doc.client_id == asset.client_id:
                doc.asset_id = asset.id

    db.commit()

    # Reload with relationships
    asset = db.execute(
        select(PatAsset)
        .options(
            joinedload(PatAsset.client),
            joinedload(PatAsset.account).joinedload(PatAccount.institution),
        )
        .where(PatAsset.id == asset.id)
    ).unique().scalar_one()

    return build_asset_response(asset)


@router.delete("/{asset_id}", status_code=204)
def delete_asset(
    asset_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Screen.ASSETS)),
):
    """Delete an asset (soft delete)."""
    asset = db.get(PatAsset, asset_id)
    if not asset:
        raise HTTPException(status_code=404, detail="Ativo não encontrado")

    check_client_access(asset.client_id, current_user, db)

    # Soft delete
    asset.is_active = False
    db.commit()
    return None
