"""Client routes."""

from decimal import Decimal
from typing import Optional
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

from starke.api.dependencies import get_db
from starke.api.dependencies.auth import get_current_user, require_permission
from starke.core.security import encrypt_cpf_cnpj, decrypt_cpf_cnpj
from starke.domain.permissions.screens import Screen
from starke.domain.services.auth_service import AuthService
from starke.infrastructure.database.models import User, UserRole
from starke.infrastructure.database.patrimony.client import PatClient
from starke.infrastructure.database.patrimony.asset import PatAsset
from starke.infrastructure.database.patrimony.liability import PatLiability
from starke.infrastructure.database.patrimony.account import PatAccount

from .schemas import (
    ClientCreate,
    ClientDetailResponse,
    ClientListResponse,
    ClientResponse,
    ClientSummaryResponse,
    ClientUpdate,
)

router = APIRouter(prefix="/clients", tags=["Clients"])


def mask_cpf_cnpj(cpf_cnpj: str) -> str:
    """Mask CPF/CNPJ for display."""
    import re
    digits = re.sub(r"[^\d]", "", cpf_cnpj)
    if len(digits) == 11:
        # CPF: XXX.XXX.XXX-XX -> ***.***.XXX-**
        return f"***.***{digits[6:9]}.-**"
    elif len(digits) == 14:
        # CNPJ: XX.XXX.XXX/XXXX-XX -> **.XXX.XXX/****-**
        return f"**.{digits[2:5]}.{digits[5:8]}/****-**"
    return "***"


def filter_by_user_access(query, current_user: User, db: Session):
    """Filter query based on user role and access."""
    if current_user.role == UserRole.CLIENT.value:
        # Client only sees their own data
        client = db.execute(
            select(PatClient).where(PatClient.user_id == current_user.id)
        ).scalar_one_or_none()
        if client:
            query = query.where(PatClient.id == client.id)
        else:
            # No client linked - return empty
            query = query.where(False)
    elif current_user.role == UserRole.RM.value:
        # RM sees only assigned clients
        query = query.where(PatClient.rm_user_id == current_user.id)
    # Admin and Analyst see all
    return query


@router.get("", response_model=ClientListResponse)
def list_clients(
    page: int = Query(1, ge=1, description="Página"),
    per_page: int = Query(20, ge=1, le=100, description="Itens por página"),
    status: Optional[str] = Query(None, description="Filtrar por status"),
    client_type: Optional[str] = Query(None, description="Filtrar por tipo (pf/pj)"),
    search: Optional[str] = Query(None, description="Buscar por nome"),
    rm_user_id: Optional[int] = Query(None, description="Filtrar por RM"),
    has_login: Optional[bool] = Query(None, description="Filtrar por vínculo com usuário (true=com login, false=sem login)"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Screen.CLIENTS)),
):
    """List all clients with pagination and access control."""
    query = select(PatClient).options(joinedload(PatClient.rm_user))

    # Apply access control filter
    query = filter_by_user_access(query, current_user, db)

    # Apply additional filters
    if status:
        query = query.where(PatClient.status == status)
    if client_type:
        query = query.where(PatClient.client_type == client_type)
    if search:
        query = query.where(PatClient.name.ilike(f"%{search}%"))
    if rm_user_id and current_user.role != UserRole.RM.value:
        # RM can't filter by other RMs
        query = query.where(PatClient.rm_user_id == rm_user_id)
    if has_login is not None:
        if has_login:
            query = query.where(PatClient.user_id.isnot(None))
        else:
            query = query.where(PatClient.user_id.is_(None))

    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total = db.execute(count_query).scalar() or 0

    # Pagination
    offset = (page - 1) * per_page
    query = query.order_by(PatClient.name).offset(offset).limit(per_page)

    items = db.execute(query).unique().scalars().all()

    response_items = []
    for client in items:
        # Decrypt CPF/CNPJ
        cpf_cnpj = decrypt_cpf_cnpj(client.cpf_cnpj_encrypted)

        response_items.append(
            ClientResponse(
                id=client.id,
                name=client.name,
                client_type=client.client_type,
                cpf_cnpj=cpf_cnpj,
                email=client.email,
                phone=client.phone,
                base_currency=client.base_currency,
                notes=client.notes,
                status=client.status,
                rm_user_id=client.rm_user_id,
                rm_user_name=client.rm_user.full_name if client.rm_user else None,
                user_id=client.user_id,
                user_email=client.user.email if client.user else None,
                has_login=client.user_id is not None,
                created_at=client.created_at,
                updated_at=client.updated_at,
            )
        )

    return ClientListResponse(
        items=response_items,
        total=total,
        page=page,
        per_page=per_page,
        pages=(total + per_page - 1) // per_page if total > 0 else 0,
    )


@router.get("/{client_id}", response_model=ClientDetailResponse)
def get_client(
    client_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Screen.CLIENTS)),
):
    """Get client by ID with summary."""
    # Check access
    query = select(PatClient).where(PatClient.id == client_id)
    query = filter_by_user_access(query, current_user, db)

    client = db.execute(query.options(joinedload(PatClient.rm_user))).unique().scalar_one_or_none()
    if not client:
        raise HTTPException(status_code=404, detail="Cliente não encontrado")

    # Calculate summary
    assets_total = db.execute(
        select(func.coalesce(func.sum(PatAsset.current_value), 0))
        .where(PatAsset.client_id == client_id)
        .where(PatAsset.is_active == True)
    ).scalar() or Decimal("0")

    liabilities_total = db.execute(
        select(func.coalesce(func.sum(PatLiability.current_balance), 0))
        .where(PatLiability.client_id == client_id)
        .where(PatLiability.is_active == True)
    ).scalar() or Decimal("0")

    accounts_count = db.execute(
        select(func.count())
        .select_from(PatAccount)
        .where(PatAccount.client_id == client_id)
        .where(PatAccount.is_active == True)
    ).scalar() or 0

    assets_count = db.execute(
        select(func.count())
        .select_from(PatAsset)
        .where(PatAsset.client_id == client_id)
        .where(PatAsset.is_active == True)
    ).scalar() or 0

    liabilities_count = db.execute(
        select(func.count())
        .select_from(PatLiability)
        .where(PatLiability.client_id == client_id)
        .where(PatLiability.is_active == True)
    ).scalar() or 0

    # Decrypt CPF/CNPJ
    cpf_cnpj = decrypt_cpf_cnpj(client.cpf_cnpj_encrypted)

    return ClientDetailResponse(
        id=client.id,
        name=client.name,
        client_type=client.client_type,
        cpf_cnpj=cpf_cnpj,
        email=client.email,
        phone=client.phone,
        base_currency=client.base_currency,
        notes=client.notes,
        status=client.status,
        rm_user_id=client.rm_user_id,
        rm_user_name=client.rm_user.full_name if client.rm_user else None,
        user_id=client.user_id,
        user_email=client.user.email if client.user else None,
        has_login=client.user_id is not None,
        created_at=client.created_at,
        updated_at=client.updated_at,
        total_assets=assets_total,
        total_liabilities=liabilities_total,
        net_worth=assets_total - liabilities_total,
        accounts_count=accounts_count,
        assets_count=assets_count,
        liabilities_count=liabilities_count,
    )


@router.post("", response_model=ClientResponse, status_code=201)
def create_client(
    data: ClientCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Screen.CLIENTS)),
):
    """Create a new client.

    If create_login is provided, also creates a user with role=client linked to the client.
    """
    # Validate create_login requirements
    if data.create_login:
        if not data.email:
            raise HTTPException(
                status_code=400,
                detail="Email é obrigatório para criar login do cliente"
            )
        # Check if email is already registered
        auth_service = AuthService(db)
        existing_user = auth_service.get_user_by_email(data.email)
        if existing_user:
            raise HTTPException(
                status_code=400,
                detail="Este email já está cadastrado como usuário"
            )

    # Encrypt CPF/CNPJ
    encrypted, hash_value = encrypt_cpf_cnpj(data.cpf_cnpj)

    # Check for duplicates by hash
    existing = db.execute(
        select(PatClient).where(PatClient.cpf_cnpj_hash == hash_value)
    ).scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=400, detail="CPF/CNPJ já cadastrado")

    # Set RM based on role
    rm_user_id = data.rm_user_id
    if current_user.role == UserRole.RM.value:
        # RM creating client - assign to themselves
        rm_user_id = current_user.id

    client = PatClient(
        id=str(uuid4()),
        name=data.name,
        client_type=data.client_type,
        cpf_cnpj_encrypted=encrypted,
        cpf_cnpj_hash=hash_value,
        email=data.email,
        phone=data.phone,
        base_currency=data.base_currency,
        notes=data.notes,
        status=data.status,
        rm_user_id=rm_user_id,
    )
    db.add(client)
    db.flush()  # Get client ID before creating user

    # Create user if requested
    created_user = None
    if data.create_login:
        auth_service = AuthService(db)
        created_user = User(
            email=data.email,
            full_name=data.name,
            hashed_password=auth_service.get_password_hash(data.create_login.password),
            role=UserRole.CLIENT.value,
            is_active=True,
            is_superuser=False,
        )
        db.add(created_user)
        db.flush()  # Get user ID

        # Link client to user
        client.user_id = created_user.id

    db.commit()
    db.refresh(client)

    return ClientResponse(
        id=client.id,
        name=client.name,
        client_type=client.client_type,
        cpf_cnpj=data.cpf_cnpj,
        email=client.email,
        phone=client.phone,
        base_currency=client.base_currency,
        notes=client.notes,
        status=client.status,
        rm_user_id=client.rm_user_id,
        user_id=client.user_id,
        user_email=created_user.email if created_user else None,
        has_login=client.user_id is not None,
        created_at=client.created_at,
        updated_at=client.updated_at,
    )


@router.put("/{client_id}", response_model=ClientResponse)
def update_client(
    client_id: str,
    data: ClientUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Screen.CLIENTS)),
):
    """Update a client."""
    # Check access
    query = select(PatClient).where(PatClient.id == client_id)
    query = filter_by_user_access(query, current_user, db)

    client = db.execute(query).scalar_one_or_none()
    if not client:
        raise HTTPException(status_code=404, detail="Cliente não encontrado")

    # RM can only update clients assigned to them
    if current_user.role == UserRole.RM.value:
        if "rm_user_id" in data.model_dump(exclude_unset=True):
            raise HTTPException(
                status_code=403, detail="RM não pode alterar atribuição de cliente"
            )

    # Update only provided fields
    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(client, field, value)

    db.commit()
    db.refresh(client)

    # Decrypt CPF/CNPJ for response
    cpf_cnpj = decrypt_cpf_cnpj(client.cpf_cnpj_encrypted)

    return ClientResponse(
        id=client.id,
        name=client.name,
        client_type=client.client_type,
        cpf_cnpj=cpf_cnpj,
        email=client.email,
        phone=client.phone,
        base_currency=client.base_currency,
        notes=client.notes,
        status=client.status,
        rm_user_id=client.rm_user_id,
        rm_user_name=client.rm_user.full_name if client.rm_user else None,
        user_id=client.user_id,
        user_email=client.user.email if client.user else None,
        has_login=client.user_id is not None,
        created_at=client.created_at,
        updated_at=client.updated_at,
    )


@router.delete("/{client_id}", status_code=204)
def delete_client(
    client_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Screen.CLIENTS)),
):
    """Delete a client (soft delete - sets status to inactive)."""
    # Check access
    query = select(PatClient).where(PatClient.id == client_id)
    query = filter_by_user_access(query, current_user, db)

    client = db.execute(query).scalar_one_or_none()
    if not client:
        raise HTTPException(status_code=404, detail="Cliente não encontrado")

    # Soft delete
    client.status = "inactive"
    db.commit()
    return None


@router.get("/{client_id}/summary", response_model=ClientSummaryResponse)
def get_client_summary(
    client_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Screen.CLIENTS)),
):
    """Get client patrimony summary."""
    # Check access
    query = select(PatClient).where(PatClient.id == client_id)
    query = filter_by_user_access(query, current_user, db)

    client = db.execute(query).scalar_one_or_none()
    if not client:
        raise HTTPException(status_code=404, detail="Cliente não encontrado")

    # Assets by category
    assets_by_category = {}
    assets_result = db.execute(
        select(PatAsset.category, func.sum(PatAsset.current_value))
        .where(PatAsset.client_id == client_id)
        .where(PatAsset.is_active == True)
        .group_by(PatAsset.category)
    ).all()
    for category, total in assets_result:
        assets_by_category[category] = total or Decimal("0")

    # Liabilities by type
    liabilities_by_type = {}
    liabilities_result = db.execute(
        select(PatLiability.liability_type, func.sum(PatLiability.current_balance))
        .where(PatLiability.client_id == client_id)
        .where(PatLiability.is_active == True)
        .group_by(PatLiability.liability_type)
    ).all()
    for liability_type, total in liabilities_result:
        liabilities_by_type[liability_type] = total or Decimal("0")

    # Totals
    total_assets = sum(assets_by_category.values(), Decimal("0"))
    total_liabilities = sum(liabilities_by_type.values(), Decimal("0"))

    # Counts
    accounts_count = db.execute(
        select(func.count())
        .select_from(PatAccount)
        .where(PatAccount.client_id == client_id)
        .where(PatAccount.is_active == True)
    ).scalar() or 0

    assets_count = db.execute(
        select(func.count())
        .select_from(PatAsset)
        .where(PatAsset.client_id == client_id)
        .where(PatAsset.is_active == True)
    ).scalar() or 0

    liabilities_count = db.execute(
        select(func.count())
        .select_from(PatLiability)
        .where(PatLiability.client_id == client_id)
        .where(PatLiability.is_active == True)
    ).scalar() or 0

    return ClientSummaryResponse(
        client_id=client_id,
        client_name=client.name,
        total_assets=total_assets,
        total_liabilities=total_liabilities,
        net_worth=total_assets - total_liabilities,
        assets_by_category=assets_by_category,
        liabilities_by_type=liabilities_by_type,
        accounts_count=accounts_count,
        assets_count=assets_count,
        liabilities_count=liabilities_count,
    )


@router.get("/{client_id}/evolution")
def get_client_evolution(
    client_id: str,
    months: int = Query(12, ge=1, le=60, description="Número de meses"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Screen.CLIENTS)),
):
    """Get client patrimony evolution over time.

    Returns monthly evolution of net worth based on monthly positions.
    """
    from starke.infrastructure.database.patrimony.monthly_position import PatMonthlyPosition

    # Check access
    query = select(PatClient).where(PatClient.id == client_id)
    query = filter_by_user_access(query, current_user, db)

    client = db.execute(query).scalar_one_or_none()
    if not client:
        raise HTTPException(status_code=404, detail="Cliente não encontrado")

    # Get monthly positions grouped by reference_date
    positions = db.execute(
        select(
            PatMonthlyPosition.reference_date,
            func.sum(PatMonthlyPosition.value).label("total_assets"),
        )
        .where(PatMonthlyPosition.client_id == client_id)
        .group_by(PatMonthlyPosition.reference_date)
        .order_by(PatMonthlyPosition.reference_date.desc())
        .limit(months)
    ).all()

    # Get current liabilities total
    current_liabilities = db.execute(
        select(func.coalesce(func.sum(PatLiability.current_balance), 0))
        .where(PatLiability.client_id == client_id)
        .where(PatLiability.is_active == True)
    ).scalar() or Decimal("0")

    evolution = []
    for pos in reversed(positions):
        total_assets = pos.total_assets or Decimal("0")
        net_worth = total_assets - current_liabilities
        evolution.append({
            "date": pos.reference_date.isoformat(),
            "total_assets": float(total_assets),
            "total_liabilities": float(current_liabilities),
            "net_worth": float(net_worth),
        })

    # Calculate variation
    variation = None
    variation_pct = None
    if len(evolution) >= 2:
        first_value = evolution[0]["net_worth"]
        last_value = evolution[-1]["net_worth"]
        variation = last_value - first_value
        if first_value != 0:
            variation_pct = (variation / first_value) * 100

    return {
        "client_id": client_id,
        "client_name": client.name,
        "period_months": months,
        "data_points": len(evolution),
        "variation": float(variation) if variation is not None else None,
        "variation_pct": float(variation_pct) if variation_pct is not None else None,
        "evolution": evolution,
    }


@router.get("/{client_id}/report/pdf")
def generate_client_report_pdf(
    client_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Screen.CLIENTS)),
):
    """Generate PDF report for a client.

    Returns PDF file with patrimony summary.
    """
    from datetime import datetime
    from fastapi.responses import Response

    # Check access
    query = select(PatClient).where(PatClient.id == client_id)
    query = filter_by_user_access(query, current_user, db)

    client = db.execute(query).scalar_one_or_none()
    if not client:
        raise HTTPException(status_code=404, detail="Cliente não encontrado")

    # Get assets grouped by category
    assets = db.execute(
        select(PatAsset)
        .where(PatAsset.client_id == client_id)
        .where(PatAsset.is_active == True)
        .order_by(PatAsset.category, PatAsset.current_value.desc())
    ).scalars().all()

    assets_by_category = {}
    total_assets = Decimal("0")
    for asset in assets:
        category = asset.category or "outros"
        if category not in assets_by_category:
            assets_by_category[category] = {"items": [], "total": Decimal("0")}
        value = asset.current_value or Decimal("0")
        assets_by_category[category]["items"].append({
            "name": asset.name,
            "value": value,
            "subcategory": asset.subcategory,
        })
        assets_by_category[category]["total"] += value
        total_assets += value

    # Get liabilities
    liabilities = db.execute(
        select(PatLiability)
        .where(PatLiability.client_id == client_id)
        .where(PatLiability.is_active == True)
        .order_by(PatLiability.current_balance.desc())
    ).scalars().all()

    total_liabilities = sum((l.current_balance or Decimal("0")) for l in liabilities)
    net_worth = total_assets - total_liabilities

    # Generate HTML content
    html_content = _generate_report_html(
        client_name=client.name,
        report_date=datetime.now(),
        total_assets=total_assets,
        total_liabilities=total_liabilities,
        net_worth=net_worth,
        assets_by_category=assets_by_category,
        liabilities=liabilities,
    )

    # Convert HTML to PDF using weasyprint if available
    try:
        from weasyprint import HTML
        pdf_content = HTML(string=html_content).write_pdf()
        return Response(
            content=pdf_content,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f"attachment; filename=relatorio_{client_id}_{datetime.now().strftime('%Y%m%d')}.pdf"
            }
        )
    except ImportError:
        # Fallback: return HTML if weasyprint not available
        return Response(
            content=html_content.encode("utf-8"),
            media_type="text/html",
            headers={
                "Content-Disposition": f"attachment; filename=relatorio_{client_id}_{datetime.now().strftime('%Y%m%d')}.html"
            }
        )


def _generate_report_html(
    client_name: str,
    report_date,
    total_assets: Decimal,
    total_liabilities: Decimal,
    net_worth: Decimal,
    assets_by_category: dict,
    liabilities: list,
) -> str:
    """Generate HTML content for the report."""
    def format_currency(value: Decimal) -> str:
        return f"R$ {float(value):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

    assets_html = ""
    for category, data in assets_by_category.items():
        assets_html += f"""
        <div class="category">
            <h3>{category.upper()}</h3>
            <table>
                <thead>
                    <tr>
                        <th>Ativo</th>
                        <th>Subcategoria</th>
                        <th style="text-align: right;">Valor</th>
                    </tr>
                </thead>
                <tbody>
        """
        for item in data["items"]:
            assets_html += f"""
                    <tr>
                        <td>{item['name']}</td>
                        <td>{item['subcategory'] or '-'}</td>
                        <td style="text-align: right;">{format_currency(item['value'])}</td>
                    </tr>
            """
        assets_html += f"""
                </tbody>
                <tfoot>
                    <tr>
                        <td colspan="2"><strong>Subtotal {category}</strong></td>
                        <td style="text-align: right;"><strong>{format_currency(data['total'])}</strong></td>
                    </tr>
                </tfoot>
            </table>
        </div>
        """

    liabilities_html = ""
    if liabilities:
        liabilities_html = """
        <div class="category">
            <h3>PASSIVOS</h3>
            <table>
                <thead>
                    <tr>
                        <th>Descrição</th>
                        <th>Tipo</th>
                        <th style="text-align: right;">Saldo</th>
                    </tr>
                </thead>
                <tbody>
        """
        for liability in liabilities:
            liabilities_html += f"""
                    <tr>
                        <td>{liability.description or liability.liability_type}</td>
                        <td>{liability.liability_type}</td>
                        <td style="text-align: right;">{format_currency(liability.current_balance or Decimal('0'))}</td>
                    </tr>
            """
        liabilities_html += f"""
                </tbody>
                <tfoot>
                    <tr>
                        <td colspan="2"><strong>Total Passivos</strong></td>
                        <td style="text-align: right;"><strong>{format_currency(total_liabilities)}</strong></td>
                    </tr>
                </tfoot>
            </table>
        </div>
        """

    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <title>Relatório Patrimonial - {client_name}</title>
        <style>
            body {{
                font-family: Arial, sans-serif;
                margin: 40px;
                color: #333;
            }}
            .header {{
                text-align: center;
                margin-bottom: 30px;
                border-bottom: 2px solid #0066cc;
                padding-bottom: 20px;
            }}
            .header h1 {{
                color: #0066cc;
                margin-bottom: 5px;
            }}
            .summary {{
                display: flex;
                justify-content: space-around;
                margin: 30px 0;
                padding: 20px;
                background: #f5f5f5;
                border-radius: 8px;
            }}
            .summary-item {{
                text-align: center;
            }}
            .summary-item .value {{
                font-size: 24px;
                font-weight: bold;
                color: #0066cc;
            }}
            .summary-item .label {{
                font-size: 12px;
                color: #666;
                margin-top: 5px;
            }}
            .category {{
                margin: 20px 0;
            }}
            .category h3 {{
                background: #0066cc;
                color: white;
                padding: 10px;
                margin-bottom: 0;
            }}
            table {{
                width: 100%;
                border-collapse: collapse;
            }}
            th, td {{
                padding: 10px;
                border: 1px solid #ddd;
            }}
            th {{
                background: #f5f5f5;
            }}
            tfoot td {{
                background: #f5f5f5;
            }}
            .footer {{
                margin-top: 30px;
                text-align: center;
                font-size: 12px;
                color: #666;
            }}
        </style>
    </head>
    <body>
        <div class="header">
            <h1>Relatório Patrimonial</h1>
            <p><strong>{client_name}</strong></p>
            <p>Data: {report_date.strftime('%d/%m/%Y')}</p>
        </div>

        <div class="summary">
            <div class="summary-item">
                <div class="value">{format_currency(total_assets)}</div>
                <div class="label">Total de Ativos</div>
            </div>
            <div class="summary-item">
                <div class="value" style="color: #cc0000;">{format_currency(total_liabilities)}</div>
                <div class="label">Total de Passivos</div>
            </div>
            <div class="summary-item">
                <div class="value" style="color: {'#009900' if net_worth >= 0 else '#cc0000'};">{format_currency(net_worth)}</div>
                <div class="label">Patrimônio Líquido</div>
            </div>
        </div>

        <h2>Detalhamento de Ativos</h2>
        {assets_html}

        {liabilities_html}

        <div class="footer">
            <p>Relatório gerado automaticamente pelo sistema Starke</p>
            <p>Este documento é confidencial e de uso exclusivo do cliente.</p>
        </div>
    </body>
    </html>
    """
