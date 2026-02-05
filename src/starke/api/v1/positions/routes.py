"""Position routes for managing monthly snapshots."""

import json
import os
from datetime import date, datetime
from decimal import Decimal
from typing import Optional
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File, Form
from sqlalchemy import func, select, and_, or_
from sqlalchemy.orm import Session, joinedload

from starke.api.dependencies import get_db
from starke.api.dependencies.auth import require_permission
from starke.domain.permissions.screens import Screen
from starke.infrastructure.database.models import User, UserRole
from starke.infrastructure.database.patrimony.client import PatClient
from starke.infrastructure.database.patrimony.asset import PatAsset
from starke.infrastructure.database.patrimony.liability import PatLiability
from starke.infrastructure.database.patrimony.monthly_position import PatMonthlyPosition
from starke.infrastructure.database.patrimony.import_history import PatImportHistory

from .schemas import (
    PositionCreate,
    PositionGenerateAll,
    PositionGenerateAllResponse,
    PositionListResponse,
    PositionResponse,
    PositionItemResponse,
    PositionItemListResponse,
    PositionImportResponse,
    PositionValidateResponse,
    ImportHistoryItem,
    ImportHistoryListResponse,
    ImportError,
)

router = APIRouter(prefix="/positions", tags=["Positions"])


def get_last_day_of_month(year: int, month: int) -> date:
    """Get the last day of a given month."""
    if month == 12:
        return date(year + 1, 1, 1).replace(day=1) - __import__("datetime").timedelta(days=1)
    return date(year, month + 1, 1) - __import__("datetime").timedelta(days=1)


def calculate_client_snapshot(client_id: str, reference_date: date, db: Session) -> dict:
    """Calculate snapshot for a client at a given date."""
    # Get assets grouped by category
    assets_by_category = {}
    assets = db.execute(
        select(PatAsset)
        .where(PatAsset.client_id == client_id)
        .where(PatAsset.is_active == True)
    ).scalars().all()

    total_assets = Decimal("0")
    for asset in assets:
        category = asset.category or "outros"
        if category not in assets_by_category:
            assets_by_category[category] = {"total": Decimal("0"), "items": []}

        value = asset.current_value or Decimal("0")
        assets_by_category[category]["items"].append({
            "asset_id": asset.id,
            "name": asset.name,
            "category": category,
            "value": float(value),
            "quantity": float(asset.quantity) if asset.quantity else None,
            "currency": asset.currency or "BRL",
        })
        assets_by_category[category]["total"] += value
        total_assets += value

    # Convert totals to float for JSON
    for cat in assets_by_category:
        assets_by_category[cat]["total"] = float(assets_by_category[cat]["total"])

    # Get liabilities
    liabilities = db.execute(
        select(PatLiability)
        .where(PatLiability.client_id == client_id)
        .where(PatLiability.is_active == True)
    ).scalars().all()

    total_liabilities = Decimal("0")
    liability_items = []
    for liability in liabilities:
        value = liability.current_balance or Decimal("0")
        liability_items.append({
            "liability_id": liability.id,
            "description": liability.description or liability.liability_type,
            "value": float(value),
            "currency": liability.currency or "BRL",
        })
        total_liabilities += value

    return {
        "total_assets": total_assets,
        "total_liabilities": total_liabilities,
        "net_worth": total_assets - total_liabilities,
        "snapshot": {
            "assets_by_category": assets_by_category,
            "liabilities": {
                "total": float(total_liabilities),
                "items": liability_items,
            },
        },
    }


def check_client_access(client_id: str, current_user: User, db: Session) -> PatClient:
    """Check if user has access to client."""
    query = select(PatClient).where(PatClient.id == client_id)

    if current_user.role == UserRole.CLIENT.value:
        query = query.where(PatClient.user_id == current_user.id)
    elif current_user.role == UserRole.RM.value:
        query = query.where(PatClient.rm_user_id == current_user.id)

    client = db.execute(query).scalar_one_or_none()
    if not client:
        raise HTTPException(status_code=404, detail="Cliente não encontrado")
    return client


@router.get("", response_model=PositionListResponse)
def list_positions(
    page: int = Query(1, ge=1, description="Página"),
    per_page: int = Query(20, ge=1, le=100, description="Itens por página"),
    client_id: Optional[str] = Query(None, description="Filtrar por cliente"),
    year: Optional[int] = Query(None, description="Filtrar por ano"),
    month: Optional[int] = Query(None, ge=1, le=12, description="Filtrar por mês"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Screen.POSITIONS)),
):
    """List all position snapshots.

    Returns consolidated monthly positions for clients.
    """
    # Base query - get distinct client/date combinations from monthly positions
    query = (
        select(
            PatMonthlyPosition.client_id,
            PatMonthlyPosition.reference_date,
            func.sum(PatMonthlyPosition.value).label("total_assets"),
        )
        .group_by(PatMonthlyPosition.client_id, PatMonthlyPosition.reference_date)
    )

    # Access control
    if current_user.role == UserRole.CLIENT.value:
        client = db.execute(
            select(PatClient).where(PatClient.user_id == current_user.id)
        ).scalar_one_or_none()
        if client:
            query = query.where(PatMonthlyPosition.client_id == client.id)
        else:
            query = query.where(False)
    elif current_user.role == UserRole.RM.value:
        client_ids = db.execute(
            select(PatClient.id).where(PatClient.rm_user_id == current_user.id)
        ).scalars().all()
        query = query.where(PatMonthlyPosition.client_id.in_(client_ids))

    # Apply filters
    if client_id:
        query = query.where(PatMonthlyPosition.client_id == client_id)
    if year:
        query = query.where(func.extract("year", PatMonthlyPosition.reference_date) == year)
    if month:
        query = query.where(func.extract("month", PatMonthlyPosition.reference_date) == month)

    # Count total
    subquery = query.subquery()
    count_query = select(func.count()).select_from(subquery)
    total = db.execute(count_query).scalar() or 0

    # Pagination
    offset = (page - 1) * per_page
    query = query.order_by(PatMonthlyPosition.reference_date.desc()).offset(offset).limit(per_page)

    results = db.execute(query).all()

    # Build responses
    items = []
    for row in results:
        client = db.get(PatClient, row.client_id)
        client_name = client.name if client else None

        # Get liabilities total for this client
        liabilities_total = db.execute(
            select(func.coalesce(func.sum(PatLiability.current_balance), 0))
            .where(PatLiability.client_id == row.client_id)
            .where(PatLiability.is_active == True)
        ).scalar() or Decimal("0")

        items.append(
            PositionResponse(
                id=f"{row.client_id}_{row.reference_date}",
                client_id=row.client_id,
                client_name=client_name,
                reference_date=row.reference_date,
                total_assets=row.total_assets or Decimal("0"),
                total_liabilities=liabilities_total,
                net_worth=(row.total_assets or Decimal("0")) - liabilities_total,
                status="processed",
                created_at=datetime.utcnow(),
            )
        )

    return PositionListResponse(
        items=items,
        total=total,
        page=page,
        per_page=per_page,
        pages=(total + per_page - 1) // per_page if total > 0 else 0,
    )


# ============================================================================
# Static routes must come BEFORE dynamic routes like /{position_id}
# ============================================================================


@router.get("/items", response_model=PositionItemListResponse)
def list_position_items(
    page: int = Query(1, ge=1, description="Página"),
    per_page: int = Query(20, ge=1, le=100, description="Itens por página"),
    search: Optional[str] = Query(None, description="Buscar por nome do cliente ou ativo"),
    client_id: Optional[str] = Query(None, description="Filtrar por cliente"),
    year: Optional[int] = Query(None, description="Filtrar por ano"),
    month: Optional[int] = Query(None, ge=1, le=12, description="Filtrar por mês"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Screen.POSITIONS)),
):
    """List individual position items.

    Returns individual asset positions with pagination and filters.
    """
    # Base query
    query = (
        select(PatMonthlyPosition)
        .join(PatClient, PatMonthlyPosition.client_id == PatClient.id)
        .join(PatAsset, PatMonthlyPosition.asset_id == PatAsset.id)
    )

    # Access control
    if current_user.role == UserRole.CLIENT.value:
        client = db.execute(
            select(PatClient).where(PatClient.user_id == current_user.id)
        ).scalar_one_or_none()
        if client:
            query = query.where(PatMonthlyPosition.client_id == client.id)
        else:
            query = query.where(False)
    elif current_user.role == UserRole.RM.value:
        client_ids = db.execute(
            select(PatClient.id).where(PatClient.rm_user_id == current_user.id)
        ).scalars().all()
        query = query.where(PatMonthlyPosition.client_id.in_(client_ids))

    # Apply filters
    if client_id:
        query = query.where(PatMonthlyPosition.client_id == client_id)
    if year:
        query = query.where(func.extract("year", PatMonthlyPosition.reference_date) == year)
    if month:
        query = query.where(func.extract("month", PatMonthlyPosition.reference_date) == month)
    if search:
        search_filter = f"%{search}%"
        query = query.where(
            or_(
                PatClient.name.ilike(search_filter),
                PatAsset.name.ilike(search_filter),
            )
        )

    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total = db.execute(count_query).scalar() or 0

    # Pagination
    offset = (page - 1) * per_page
    query = query.order_by(PatMonthlyPosition.reference_date.desc()).offset(offset).limit(per_page)

    results = db.execute(query).scalars().all()

    # Build responses
    items = []
    for position in results:
        client = db.get(PatClient, position.client_id)
        asset = db.get(PatAsset, position.asset_id)

        items.append(
            PositionItemResponse(
                id=position.id,
                reference_date=position.reference_date,
                client_id=position.client_id,
                client_name=client.name if client else None,
                asset_name=asset.name if asset else "N/A",
                value=position.value,
                currency=position.currency,
                source=position.source,
            )
        )

    return PositionItemListResponse(
        items=items,
        total=total,
        page=page,
        per_page=per_page,
        pages=(total + per_page - 1) // per_page if total > 0 else 0,
    )


@router.get("/validate", response_model=PositionValidateResponse)
def validate_positions(
    year: int = Query(..., description="Ano para validação"),
    month: int = Query(..., ge=1, le=12, description="Mês para validação"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Screen.POSITIONS)),
):
    """Validate position data for a given period.

    Checks for data integrity and returns validation results.
    """
    # Get all positions for the period
    query = (
        select(PatMonthlyPosition)
        .where(func.extract("year", PatMonthlyPosition.reference_date) == year)
        .where(func.extract("month", PatMonthlyPosition.reference_date) == month)
    )

    # Access control
    if current_user.role == UserRole.CLIENT.value:
        client = db.execute(
            select(PatClient).where(PatClient.user_id == current_user.id)
        ).scalar_one_or_none()
        if client:
            query = query.where(PatMonthlyPosition.client_id == client.id)
        else:
            query = query.where(False)
    elif current_user.role == UserRole.RM.value:
        client_ids = db.execute(
            select(PatClient.id).where(PatClient.rm_user_id == current_user.id)
        ).scalars().all()
        query = query.where(PatMonthlyPosition.client_id.in_(client_ids))

    positions = db.execute(query).scalars().all()
    total_items = len(positions)

    errors = []
    valid_count = 0

    for idx, position in enumerate(positions, start=1):
        has_error = False

        # Validate value is positive
        if position.value < 0:
            errors.append(ImportError(
                row=idx,
                field="value",
                message=f"Valor negativo para posição {position.id}"
            ))
            has_error = True

        # Validate client exists
        client = db.get(PatClient, position.client_id)
        if not client:
            errors.append(ImportError(
                row=idx,
                field="client_id",
                message=f"Cliente não encontrado para posição {position.id}"
            ))
            has_error = True

        # Validate asset exists
        asset = db.get(PatAsset, position.asset_id)
        if not asset:
            errors.append(ImportError(
                row=idx,
                field="asset_id",
                message=f"Ativo não encontrado para posição {position.id}"
            ))
            has_error = True

        if not has_error:
            valid_count += 1

    return PositionValidateResponse(
        total_items=total_items,
        valid_count=valid_count,
        invalid_count=len(errors),
        errors=errors,
    )


@router.get("/import-history", response_model=ImportHistoryListResponse)
def list_import_history(
    page: int = Query(1, ge=1, description="Página"),
    per_page: int = Query(20, ge=1, le=100, description="Itens por página"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Screen.POSITIONS)),
):
    """List import history.

    Returns paginated list of all position imports.
    """
    # Base query
    query = select(PatImportHistory)

    # Count total
    count_query = select(func.count()).select_from(PatImportHistory)
    total = db.execute(count_query).scalar() or 0

    # Pagination
    offset = (page - 1) * per_page
    query = query.order_by(PatImportHistory.created_at.desc()).offset(offset).limit(per_page)

    results = db.execute(query).scalars().all()

    # Build response
    items = [
        ImportHistoryItem(
            id=record.id,
            file_name=record.file_name,
            reference_date=record.reference_date,
            imported_count=record.imported_count,
            status=record.status,
            uploaded_by=record.uploaded_by,
            created_at=record.created_at,
        )
        for record in results
    ]

    return ImportHistoryListResponse(
        items=items,
        total=total,
        page=page,
        per_page=per_page,
        pages=(total + per_page - 1) // per_page if total > 0 else 0,
    )


@router.post("/import", response_model=PositionImportResponse)
async def import_positions(
    file: UploadFile = File(..., description="Arquivo de planilha (xlsx, csv)"),
    reference_date: str = Form(..., description="Data de referência (YYYY-MM-DD)"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Screen.POSITIONS)),
):
    """Import positions from a spreadsheet file.

    Accepts xlsx or csv files with position data.
    """
    # Validate file type
    if not file.filename:
        raise HTTPException(status_code=400, detail="Nome do arquivo não fornecido")

    allowed_extensions = [".xlsx", ".xls", ".csv"]
    file_ext = os.path.splitext(file.filename)[1].lower()
    if file_ext not in allowed_extensions:
        raise HTTPException(
            status_code=400,
            detail=f"Tipo de arquivo não suportado. Use: {', '.join(allowed_extensions)}",
        )

    # Validate reference_date format
    try:
        ref_date = date.fromisoformat(reference_date)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail="Data de referência inválida. Use o formato YYYY-MM-DD",
        )

    # Create import history record
    import_id = str(uuid4())
    import_record = PatImportHistory(
        id=import_id,
        file_name=file.filename,
        reference_date=reference_date,
        status="processing",
        uploaded_by=current_user.email if hasattr(current_user, 'email') else None,
        # Note: uploaded_by_id not used since users table has integer IDs
    )
    db.add(import_record)
    db.commit()

    errors = []
    imported_count = 0

    try:
        # Read file content
        content = await file.read()
        import_record.file_size = len(content)

        # Process based on file type
        if file_ext == ".csv":
            imported_count, errors = await _process_csv_import(
                content, ref_date, current_user, db
            )
        else:
            imported_count, errors = await _process_excel_import(
                content, ref_date, current_user, db
            )

        # Update import record
        import_record.imported_count = imported_count
        import_record.error_count = len(errors)
        import_record.status = "success" if not errors else "partial"
        import_record.completed_at = datetime.utcnow()
        if errors:
            import_record.errors = json.dumps([e.model_dump() for e in errors])

        db.commit()

    except Exception as e:
        import_record.status = "error"
        import_record.errors = json.dumps([{"row": 0, "message": str(e)}])
        import_record.completed_at = datetime.utcnow()
        db.commit()
        raise HTTPException(status_code=500, detail=f"Erro ao processar arquivo: {str(e)}")

    return PositionImportResponse(
        success=len(errors) == 0,
        imported_count=imported_count,
        errors=errors,
        created_at=import_record.created_at,
    )


async def _process_csv_import(
    content: bytes, ref_date: date, current_user: User, db: Session
) -> tuple[int, list[ImportError]]:
    """Process CSV file import."""
    import csv
    import io

    errors = []
    imported_count = 0

    try:
        # Decode content
        text_content = content.decode("utf-8-sig")
        reader = csv.DictReader(io.StringIO(text_content))

        for row_num, row in enumerate(reader, start=2):  # Start at 2 (header is row 1)
            try:
                # Validate required fields
                client_id = row.get("client_id", "").strip()
                asset_id = row.get("asset_id", "").strip()
                value_str = row.get("value", "").strip()

                if not client_id:
                    errors.append(ImportError(row=row_num, field="client_id", message="client_id é obrigatório"))
                    continue
                if not asset_id:
                    errors.append(ImportError(row=row_num, field="asset_id", message="asset_id é obrigatório"))
                    continue
                if not value_str:
                    errors.append(ImportError(row=row_num, field="value", message="value é obrigatório"))
                    continue

                # Parse value
                try:
                    value = Decimal(value_str.replace(",", "."))
                except:
                    errors.append(ImportError(row=row_num, field="value", message="Valor inválido"))
                    continue

                # Validate client exists
                client = db.get(PatClient, client_id)
                if not client:
                    errors.append(ImportError(row=row_num, field="client_id", message="Cliente não encontrado"))
                    continue

                # Validate asset exists
                asset = db.get(PatAsset, asset_id)
                if not asset:
                    errors.append(ImportError(row=row_num, field="asset_id", message="Ativo não encontrado"))
                    continue

                # Create or update position
                existing = db.execute(
                    select(PatMonthlyPosition)
                    .where(PatMonthlyPosition.asset_id == asset_id)
                    .where(PatMonthlyPosition.reference_date == ref_date)
                ).scalar_one_or_none()

                if existing:
                    existing.value = value
                    existing.source = "spreadsheet"
                else:
                    position = PatMonthlyPosition(
                        id=str(uuid4()),
                        client_id=client_id,
                        asset_id=asset_id,
                        reference_date=ref_date,
                        value=value,
                        quantity=Decimal(row.get("quantity", "0") or "0"),
                        currency=row.get("currency", "BRL") or "BRL",
                        source="spreadsheet",
                    )
                    db.add(position)

                # Update asset's current_value if this is the most recent position
                latest_position = db.execute(
                    select(PatMonthlyPosition.reference_date)
                    .where(PatMonthlyPosition.asset_id == asset_id)
                    .order_by(PatMonthlyPosition.reference_date.desc())
                    .limit(1)
                ).scalar_one_or_none()

                if latest_position is None or ref_date >= latest_position:
                    asset.current_value = value

                imported_count += 1

            except Exception as e:
                errors.append(ImportError(row=row_num, message=str(e)))

        db.commit()

    except Exception as e:
        errors.append(ImportError(row=0, message=f"Erro ao ler CSV: {str(e)}"))

    return imported_count, errors


async def _process_excel_import(
    content: bytes, ref_date: date, current_user: User, db: Session
) -> tuple[int, list[ImportError]]:
    """Process Excel file import."""
    errors = []
    imported_count = 0

    try:
        import openpyxl
        import io

        workbook = openpyxl.load_workbook(io.BytesIO(content), data_only=True)
        sheet = workbook.active

        if not sheet:
            errors.append(ImportError(row=0, message="Planilha vazia"))
            return imported_count, errors

        # Get headers from first row
        headers = [cell.value for cell in sheet[1] if cell.value]
        header_map = {h.lower().strip(): i for i, h in enumerate(headers)}

        # Process rows
        for row_num, row in enumerate(sheet.iter_rows(min_row=2, values_only=True), start=2):
            try:
                if not any(row):  # Skip empty rows
                    continue

                # Get values by header
                def get_val(name):
                    idx = header_map.get(name.lower())
                    return row[idx] if idx is not None and idx < len(row) else None

                client_id = str(get_val("client_id") or "").strip()
                asset_id = str(get_val("asset_id") or "").strip()
                value_raw = get_val("value")

                if not client_id:
                    errors.append(ImportError(row=row_num, field="client_id", message="client_id é obrigatório"))
                    continue
                if not asset_id:
                    errors.append(ImportError(row=row_num, field="asset_id", message="asset_id é obrigatório"))
                    continue
                if value_raw is None:
                    errors.append(ImportError(row=row_num, field="value", message="value é obrigatório"))
                    continue

                # Parse value
                try:
                    value = Decimal(str(value_raw).replace(",", "."))
                except:
                    errors.append(ImportError(row=row_num, field="value", message="Valor inválido"))
                    continue

                # Validate client
                client = db.get(PatClient, client_id)
                if not client:
                    errors.append(ImportError(row=row_num, field="client_id", message="Cliente não encontrado"))
                    continue

                # Validate asset
                asset = db.get(PatAsset, asset_id)
                if not asset:
                    errors.append(ImportError(row=row_num, field="asset_id", message="Ativo não encontrado"))
                    continue

                # Create or update position
                existing = db.execute(
                    select(PatMonthlyPosition)
                    .where(PatMonthlyPosition.asset_id == asset_id)
                    .where(PatMonthlyPosition.reference_date == ref_date)
                ).scalar_one_or_none()

                if existing:
                    existing.value = value
                    existing.source = "spreadsheet"
                else:
                    quantity_raw = get_val("quantity")
                    quantity = Decimal(str(quantity_raw or "0").replace(",", ".")) if quantity_raw else Decimal("0")

                    position = PatMonthlyPosition(
                        id=str(uuid4()),
                        client_id=client_id,
                        asset_id=asset_id,
                        reference_date=ref_date,
                        value=value,
                        quantity=quantity,
                        currency=str(get_val("currency") or "BRL"),
                        source="spreadsheet",
                    )
                    db.add(position)

                # Update asset's current_value if this is the most recent position
                latest_position = db.execute(
                    select(PatMonthlyPosition.reference_date)
                    .where(PatMonthlyPosition.asset_id == asset_id)
                    .order_by(PatMonthlyPosition.reference_date.desc())
                    .limit(1)
                ).scalar_one_or_none()

                if latest_position is None or ref_date >= latest_position:
                    asset.current_value = value

                imported_count += 1

            except Exception as e:
                errors.append(ImportError(row=row_num, message=str(e)))

        db.commit()

    except ImportError as ie:
        errors.append(ImportError(row=0, message="Biblioteca openpyxl não instalada. Use: pip install openpyxl"))
    except Exception as e:
        errors.append(ImportError(row=0, message=f"Erro ao ler Excel: {str(e)}"))

    return imported_count, errors


# ============================================================================
# Dynamic routes with path parameters
# ============================================================================


@router.get("/{position_id}", response_model=PositionResponse)
def get_position(
    position_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Screen.POSITIONS)),
):
    """Get position details with full snapshot.

    Position ID format: {client_id}_{reference_date}
    """
    # Parse position ID
    try:
        parts = position_id.rsplit("_", 1)
        client_id = parts[0]
        ref_date = date.fromisoformat(parts[1])
    except (ValueError, IndexError):
        raise HTTPException(status_code=400, detail="ID de posição inválido")

    # Check access
    client = check_client_access(client_id, current_user, db)

    # Calculate snapshot
    snapshot_data = calculate_client_snapshot(client_id, ref_date, db)

    return PositionResponse(
        id=position_id,
        client_id=client_id,
        client_name=client.name,
        reference_date=ref_date,
        total_assets=snapshot_data["total_assets"],
        total_liabilities=snapshot_data["total_liabilities"],
        net_worth=snapshot_data["net_worth"],
        status="processed",
        snapshot=snapshot_data["snapshot"],
        created_at=datetime.utcnow(),
    )


@router.post("", response_model=PositionResponse, status_code=201)
def create_position(
    data: PositionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Screen.POSITIONS)),
):
    """Create a monthly position snapshot for a client.

    The reference_date should be the last day of the month.
    """
    # Check access
    client = check_client_access(data.client_id, current_user, db)

    # Validate date is last day of month
    last_day = get_last_day_of_month(data.reference_date.year, data.reference_date.month)
    if data.reference_date != last_day:
        raise HTTPException(
            status_code=400,
            detail=f"A data de referência deve ser o último dia do mês ({last_day})",
        )

    # Check if already exists
    existing = db.execute(
        select(PatMonthlyPosition)
        .where(PatMonthlyPosition.client_id == data.client_id)
        .where(PatMonthlyPosition.reference_date == data.reference_date)
    ).scalar_one_or_none()
    if existing:
        raise HTTPException(
            status_code=409,
            detail="Já existe um snapshot para este cliente/período",
        )

    # Get current assets and create positions
    assets = db.execute(
        select(PatAsset)
        .where(PatAsset.client_id == data.client_id)
        .where(PatAsset.is_active == True)
    ).scalars().all()

    for asset in assets:
        position = PatMonthlyPosition(
            id=str(uuid4()),
            client_id=data.client_id,
            asset_id=asset.id,
            reference_date=data.reference_date,
            value=asset.current_value or Decimal("0"),
            quantity=asset.quantity,
            currency=asset.currency or "BRL",
            source="manual",
        )
        db.add(position)

    db.commit()

    # Return calculated snapshot
    snapshot_data = calculate_client_snapshot(data.client_id, data.reference_date, db)

    return PositionResponse(
        id=f"{data.client_id}_{data.reference_date}",
        client_id=data.client_id,
        client_name=client.name,
        reference_date=data.reference_date,
        total_assets=snapshot_data["total_assets"],
        total_liabilities=snapshot_data["total_liabilities"],
        net_worth=snapshot_data["net_worth"],
        status="processed",
        snapshot=snapshot_data["snapshot"],
        created_at=datetime.utcnow(),
    )


@router.post("/generate-all", response_model=PositionGenerateAllResponse)
def generate_all_positions(
    data: PositionGenerateAll,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Screen.POSITIONS)),
):
    """Generate position snapshots for all active clients.

    This is typically run at the end of each month.
    """
    # Validate date
    last_day = get_last_day_of_month(data.reference_date.year, data.reference_date.month)
    if data.reference_date != last_day:
        raise HTTPException(
            status_code=400,
            detail=f"A data de referência deve ser o último dia do mês ({last_day})",
        )

    # Get all active clients
    clients = db.execute(
        select(PatClient).where(PatClient.status == "active")
    ).scalars().all()

    total_generated = 0
    total_skipped = 0
    errors = []

    for client in clients:
        try:
            # Check if exists
            existing = db.execute(
                select(PatMonthlyPosition)
                .where(PatMonthlyPosition.client_id == client.id)
                .where(PatMonthlyPosition.reference_date == data.reference_date)
            ).first()

            if existing and not data.overwrite:
                total_skipped += 1
                continue

            if existing and data.overwrite:
                # Delete existing positions for this client/date
                db.execute(
                    PatMonthlyPosition.__table__.delete().where(
                        and_(
                            PatMonthlyPosition.client_id == client.id,
                            PatMonthlyPosition.reference_date == data.reference_date,
                        )
                    )
                )

            # Get assets and create positions
            assets = db.execute(
                select(PatAsset)
                .where(PatAsset.client_id == client.id)
                .where(PatAsset.is_active == True)
            ).scalars().all()

            for asset in assets:
                position = PatMonthlyPosition(
                    id=str(uuid4()),
                    client_id=client.id,
                    asset_id=asset.id,
                    reference_date=data.reference_date,
                    value=asset.current_value or Decimal("0"),
                    quantity=asset.quantity,
                    currency=asset.currency or "BRL",
                    source="batch",
                )
                db.add(position)

            total_generated += 1

        except Exception as e:
            errors.append({
                "client_id": client.id,
                "client_name": client.name,
                "error": str(e),
            })

    db.commit()

    return PositionGenerateAllResponse(
        total_clients=len(clients),
        total_generated=total_generated,
        total_skipped=total_skipped,
        errors=errors,
    )


@router.delete("/{position_id}", status_code=204)
def delete_position(
    position_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Screen.POSITIONS)),
):
    """Delete a position snapshot.

    Position ID format: {client_id}_{reference_date}
    """
    # Parse position ID
    try:
        parts = position_id.rsplit("_", 1)
        client_id = parts[0]
        ref_date = date.fromisoformat(parts[1])
    except (ValueError, IndexError):
        raise HTTPException(status_code=400, detail="ID de posição inválido")

    # Check access
    check_client_access(client_id, current_user, db)

    # Delete positions
    result = db.execute(
        PatMonthlyPosition.__table__.delete().where(
            and_(
                PatMonthlyPosition.client_id == client_id,
                PatMonthlyPosition.reference_date == ref_date,
            )
        )
    )

    if result.rowcount == 0:
        raise HTTPException(status_code=404, detail="Posição não encontrada")

    db.commit()
    return None
