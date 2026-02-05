"""Client self-service routes for API v1.

These endpoints are for clients to view their own data.
All data is automatically filtered for the logged-in client.
"""

from datetime import date
from decimal import Decimal
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from starke.api.dependencies.database import get_db
from starke.api.dependencies.auth import require_permission
from starke.api.v1.auth.schemas import UserPreferences
from starke.domain.permissions.screens import Screen
from starke.domain.services.currency_service import CurrencyService
from starke.infrastructure.database.models import User, UserRole
from starke.infrastructure.database.patrimony.client import PatClient
from starke.infrastructure.database.patrimony.asset import PatAsset
from starke.infrastructure.database.patrimony.liability import PatLiability
from starke.infrastructure.database.patrimony.document import PatDocument
from starke.infrastructure.database.patrimony.monthly_position import PatMonthlyPosition
from starke.infrastructure.external_apis.bcb_quotation_client import BCBQuotationClient

router = APIRouter()

# Reuse same client instance for caching
_bcb_client: Optional[BCBQuotationClient] = None


def get_currency_service() -> CurrencyService:
    """Get currency service with shared BCB client for caching."""
    global _bcb_client
    if _bcb_client is None:
        _bcb_client = BCBQuotationClient()
    return CurrencyService(_bcb_client)


def get_user_target_currency(user: User) -> str:
    """Get user's preferred currency from preferences."""
    if user.preferences:
        prefs = UserPreferences(**user.preferences)
        return prefs.default_currency
    return "BRL"


def get_currency_metadata(
    target_currency: str,
    currency_service: CurrencyService,
    ref_date: Optional[date] = None,
) -> dict:
    """Get currency conversion metadata for response.

    Returns dict with:
    - currency: target currency code
    - exchange_rate: rate from BRL to target (or None if BRL)
    - exchange_date: date of the exchange rate
    """
    if target_currency == "BRL":
        return {
            "currency": "BRL",
            "exchange_rate": None,
            "exchange_date": None,
        }

    if ref_date is None:
        ref_date = date.today()

    rate = currency_service.client.get_quotation(target_currency, ref_date)

    return {
        "currency": target_currency,
        "exchange_rate": float(rate) if rate else None,
        "exchange_date": ref_date.isoformat(),
    }


def get_client_user(
    current_user: Annotated[User, Depends(require_permission(Screen.MY_PORTFOLIO))],
) -> User:
    """Verify user is a client and return the user.

    Used by all /me endpoints to ensure only clients can access.
    """
    if current_user.role != UserRole.CLIENT.value:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This endpoint is only available for client users",
        )
    return current_user


def get_client_profile(user: User, db: Session) -> PatClient:
    """Get the PatClient associated with the user."""
    client = db.execute(
        select(PatClient).where(PatClient.user_id == user.id)
    ).scalar_one_or_none()
    if not client:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Client profile not found",
        )
    return client


@router.get("/dashboard")
def get_my_dashboard(
    current_user: Annotated[User, Depends(get_client_user)],
    db: Annotated[Session, Depends(get_db)],
) -> dict:
    """Get client's dashboard summary.

    Returns:
    - Net worth (total assets - total liabilities)
    - Asset composition by category
    - Monthly variation (percentage change from previous month)
    - Currency conversion based on user preferences

    All monetary values are converted to user's preferred currency.
    """
    from dateutil.relativedelta import relativedelta

    client = get_client_profile(current_user, db)

    # Get user's preferred currency
    target_currency = get_user_target_currency(current_user)
    currency_service = get_currency_service()

    # Calculate total assets by category
    assets = db.execute(
        select(PatAsset)
        .where(PatAsset.client_id == client.id)
        .where(PatAsset.is_active == True)
    ).scalars().all()

    total_assets = Decimal("0")
    composition = {}
    for asset in assets:
        value = asset.current_value or Decimal("0")
        asset_currency = asset.currency or "BRL"

        # Convert value to target currency
        if asset_currency != target_currency:
            converted = currency_service.convert(value, asset_currency, target_currency)
            if converted is not None:
                value = converted

        total_assets += value
        category = asset.category or "outros"
        if category not in composition:
            composition[category] = Decimal("0")
        composition[category] += value

    # Calculate total liabilities (assume all in BRL for now)
    liabilities = db.execute(
        select(PatLiability)
        .where(PatLiability.client_id == client.id)
        .where(PatLiability.is_active == True)
    ).scalars().all()

    total_liabilities = Decimal("0")
    for liability in liabilities:
        value = liability.current_balance or Decimal("0")
        # Liabilities are in BRL, convert if needed
        if target_currency != "BRL":
            converted = currency_service.convert(value, "BRL", target_currency)
            if converted is not None:
                value = converted
        total_liabilities += value

    net_worth = total_assets - total_liabilities

    # Calculate monthly variation from previous month
    # Get the last 2 months of positions to calculate variation
    today = date.today()
    last_month = today - relativedelta(months=1)

    # Get previous month's net worth from monthly positions
    previous_positions = db.execute(
        select(func.sum(PatMonthlyPosition.value))
        .where(PatMonthlyPosition.client_id == client.id)
        .where(PatMonthlyPosition.reference_date >= last_month.replace(day=1))
        .where(PatMonthlyPosition.reference_date < today.replace(day=1))
    ).scalar() or Decimal("0")

    # Convert previous month value if needed
    if target_currency != "BRL" and previous_positions > 0:
        converted = currency_service.convert(previous_positions, "BRL", target_currency, last_month)
        if converted is not None:
            previous_positions = converted

    # Calculate previous net worth (assets - liabilities)
    # Note: We use current liabilities as approximation since we don't have historical liability data
    previous_net_worth = previous_positions - total_liabilities

    # Calculate variation
    monthly_variation = None
    monthly_variation_pct = None
    if previous_net_worth != 0:
        monthly_variation = float(net_worth - previous_net_worth)
        monthly_variation_pct = float((net_worth - previous_net_worth) / abs(previous_net_worth) * 100)

    # Get currency metadata
    currency_meta = get_currency_metadata(target_currency, currency_service)

    return {
        "client_id": client.id,
        "client_name": client.name,
        **currency_meta,
        "data": {
            "net_worth": float(net_worth),
            "total_assets": float(total_assets),
            "total_liabilities": float(total_liabilities),
            "monthly_variation": monthly_variation,
            "monthly_variation_pct": monthly_variation_pct,
            "composition": [
                {"category": cat, "value": float(val), "percentage": float(val / total_assets * 100) if total_assets > 0 else 0}
                for cat, val in composition.items()
            ],
        },
    }


@router.get("/assets")
def get_my_assets(
    current_user: Annotated[User, Depends(get_client_user)],
    db: Annotated[Session, Depends(get_db)],
    category: Optional[str] = Query(None, description="Filtrar por categoria"),
) -> dict:
    """Get client's assets.

    Returns all assets belonging to the logged-in client.
    Values are converted to user's preferred currency.
    Original currency values are preserved as original_* fields.
    """
    client = get_client_profile(current_user, db)

    # Get user's preferred currency
    target_currency = get_user_target_currency(current_user)
    currency_service = get_currency_service()

    query = (
        select(PatAsset)
        .where(PatAsset.client_id == client.id)
        .where(PatAsset.is_active == True)
    )

    if category:
        query = query.where(PatAsset.category == category)

    assets = db.execute(query.order_by(PatAsset.current_value.desc())).scalars().all()

    # Get last document for each asset
    def get_last_document(asset_id: str):
        doc = db.execute(
            select(PatDocument)
            .where(PatDocument.asset_id == asset_id)
            .order_by(PatDocument.created_at.desc())
            .limit(1)
        ).scalar_one_or_none()
        if doc:
            return {
                "id": doc.id,
                "title": doc.title,
                "document_type": doc.document_type,
                "file_name": doc.file_name,
                "created_at": doc.created_at.isoformat() if doc.created_at else None,
            }
        return None

    # Build asset list with currency conversion
    asset_list = []
    for asset in assets:
        asset_currency = asset.currency or "BRL"
        current_value = asset.current_value or Decimal("0")
        base_value = asset.base_value or Decimal("0")

        # Convert values if needed
        converted_current = current_value
        converted_base = base_value
        if asset_currency != target_currency:
            conv = currency_service.convert(current_value, asset_currency, target_currency)
            if conv is not None:
                converted_current = conv
            conv = currency_service.convert(base_value, asset_currency, target_currency)
            if conv is not None:
                converted_base = conv

        asset_data = {
            "id": asset.id,
            "name": asset.name,
            "category": asset.category,
            "subcategory": asset.subcategory,
            "current_value": float(converted_current),
            "base_value": float(converted_base),
            "original_currency": asset_currency,
            "original_current_value": float(current_value),
            "original_base_value": float(base_value),
            "quantity": float(asset.quantity) if asset.quantity else None,
            "base_date": asset.base_date.isoformat() if asset.base_date else None,
            "institution_name": asset.account.institution.name if asset.account and asset.account.institution else None,
            "last_document": get_last_document(asset.id),
        }
        asset_list.append(asset_data)

    # Get currency metadata
    currency_meta = get_currency_metadata(target_currency, currency_service)

    return {
        "client_id": client.id,
        "total": len(assets),
        **currency_meta,
        "assets": asset_list,
    }


@router.get("/liabilities")
def get_my_liabilities(
    current_user: Annotated[User, Depends(get_client_user)],
    db: Annotated[Session, Depends(get_db)],
) -> dict:
    """Get client's liabilities.

    Returns all liabilities belonging to the logged-in client.
    Values are converted to user's preferred currency.
    """
    client = get_client_profile(current_user, db)

    # Get user's preferred currency
    target_currency = get_user_target_currency(current_user)
    currency_service = get_currency_service()

    liabilities = db.execute(
        select(PatLiability)
        .where(PatLiability.client_id == client.id)
        .where(PatLiability.is_active == True)
        .order_by(PatLiability.current_balance.desc())
    ).scalars().all()

    # Get last document for each liability
    def get_last_document(liability_id: str):
        doc = db.execute(
            select(PatDocument)
            .where(PatDocument.liability_id == liability_id)
            .order_by(PatDocument.created_at.desc())
            .limit(1)
        ).scalar_one_or_none()
        if doc:
            return {
                "id": doc.id,
                "title": doc.title,
                "document_type": doc.document_type,
                "file_name": doc.file_name,
                "created_at": doc.created_at.isoformat() if doc.created_at else None,
            }
        return None

    # Build liability list with currency conversion
    liability_list = []
    total_value = Decimal("0")
    total_monthly_payment = Decimal("0")

    for liability in liabilities:
        # Assume liabilities are in BRL (typical for Brazilian market)
        current_balance = liability.current_balance or Decimal("0")
        original_amount = liability.original_amount or Decimal("0")
        monthly_payment = liability.monthly_payment or Decimal("0")

        # Convert values if needed
        converted_balance = current_balance
        converted_original = original_amount
        converted_monthly = monthly_payment

        if target_currency != "BRL":
            conv = currency_service.convert(current_balance, "BRL", target_currency)
            if conv is not None:
                converted_balance = conv
            conv = currency_service.convert(original_amount, "BRL", target_currency)
            if conv is not None:
                converted_original = conv
            conv = currency_service.convert(monthly_payment, "BRL", target_currency)
            if conv is not None:
                converted_monthly = conv

        total_value += converted_balance
        total_monthly_payment += converted_monthly

        liability_data = {
            "id": liability.id,
            "liability_type": liability.liability_type,
            "description": liability.description,
            "current_balance": float(converted_balance),
            "original_amount": float(converted_original),
            "monthly_payment": float(converted_monthly),
            "original_currency": "BRL",
            "original_current_balance": float(current_balance),
            "original_original_amount": float(original_amount),
            "original_monthly_payment": float(monthly_payment),
            "interest_rate": float(liability.interest_rate) if liability.interest_rate else None,
            "start_date": liability.start_date.isoformat() if liability.start_date else None,
            "end_date": liability.end_date.isoformat() if liability.end_date else None,
            "institution_name": liability.institution.name if liability.institution else None,
            "last_document": get_last_document(liability.id),
        }
        liability_list.append(liability_data)

    # Get currency metadata
    currency_meta = get_currency_metadata(target_currency, currency_service)

    return {
        "client_id": client.id,
        "total": len(liabilities),
        "total_value": float(total_value),
        "total_monthly_payment": float(total_monthly_payment),
        **currency_meta,
        "liabilities": liability_list,
    }


@router.get("/documents")
def get_my_documents(
    current_user: Annotated[User, Depends(get_client_user)],
    db: Annotated[Session, Depends(get_db)],
    document_type: Optional[str] = Query(None, description="Filtrar por tipo"),
) -> dict:
    """Get client's documents.

    Returns all documents belonging to the logged-in client.
    """
    client = get_client_profile(current_user, db)

    query = select(PatDocument).where(PatDocument.client_id == client.id)

    if document_type:
        query = query.where(PatDocument.document_type == document_type)

    documents = db.execute(
        query.order_by(PatDocument.created_at.desc())
    ).scalars().all()

    return {
        "client_id": client.id,
        "total": len(documents),
        "documents": [
            {
                "id": doc.id,
                "document_type": doc.document_type,
                "title": doc.title,
                "description": doc.description,
                "file_name": doc.file_name,
                "file_size": doc.file_size,
                "mime_type": doc.mime_type,
                "reference_date": doc.reference_date.isoformat() if doc.reference_date else None,
                "created_at": doc.created_at.isoformat() if doc.created_at else None,
            }
            for doc in documents
        ],
    }


@router.get("/documents/{document_id}/download")
def download_my_document(
    document_id: str,
    current_user: Annotated[User, Depends(get_client_user)],
    db: Annotated[Session, Depends(get_db)],
):
    """Download a document.

    Returns file for download.
    """
    from io import BytesIO
    from fastapi.responses import FileResponse, StreamingResponse
    from starke.core.storage import get_storage

    client = get_client_profile(current_user, db)

    doc = db.execute(
        select(PatDocument)
        .where(PatDocument.id == document_id)
        .where(PatDocument.client_id == client.id)
    ).scalar_one_or_none()

    if not doc:
        raise HTTPException(status_code=404, detail="Documento não encontrado")

    storage = get_storage()

    if not storage.exists(doc.s3_key):
        raise HTTPException(status_code=404, detail="Arquivo não encontrado")

    # For local storage, use FileResponse for better performance
    if storage.is_local:
        local_path = storage.get_local_path(doc.s3_key)
        return FileResponse(
            path=local_path,
            filename=doc.file_name,
            media_type=doc.mime_type or "application/octet-stream",
        )

    # For S3, stream the content
    content = storage.download(doc.s3_key)
    return StreamingResponse(
        BytesIO(content),
        media_type=doc.mime_type or "application/octet-stream",
        headers={"Content-Disposition": f'attachment; filename="{doc.file_name}"'},
    )


@router.get("/evolution")
def get_my_evolution(
    current_user: Annotated[User, Depends(get_client_user)],
    db: Annotated[Session, Depends(get_db)],
    months: int = Query(12, ge=1, le=60, description="Número de meses"),
) -> dict:
    """Get client's patrimony evolution over time.

    Returns monthly evolution of net worth based on monthly positions.
    Values are converted using historical exchange rates for each period.
    """
    client = get_client_profile(current_user, db)

    # Get user's preferred currency
    target_currency = get_user_target_currency(current_user)
    currency_service = get_currency_service()

    # Get monthly positions grouped by reference_date
    positions = db.execute(
        select(
            PatMonthlyPosition.reference_date,
            func.sum(PatMonthlyPosition.value).label("total_assets"),
        )
        .where(PatMonthlyPosition.client_id == client.id)
        .group_by(PatMonthlyPosition.reference_date)
        .order_by(PatMonthlyPosition.reference_date.desc())
        .limit(months)
    ).all()

    # Get current liabilities total (simplified - same for all periods)
    current_liabilities_brl = db.execute(
        select(func.coalesce(func.sum(PatLiability.current_balance), 0))
        .where(PatLiability.client_id == client.id)
        .where(PatLiability.is_active == True)
    ).scalar() or Decimal("0")

    evolution = []
    for pos in reversed(positions):
        total_assets_brl = pos.total_assets or Decimal("0")
        ref_date = pos.reference_date

        # Convert using historical exchange rate for this date
        if target_currency != "BRL":
            converted_assets = currency_service.convert(
                total_assets_brl, "BRL", target_currency, ref_date
            )
            converted_liabilities = currency_service.convert(
                current_liabilities_brl, "BRL", target_currency, ref_date
            )
            total_assets = converted_assets if converted_assets is not None else total_assets_brl
            current_liabilities = converted_liabilities if converted_liabilities is not None else current_liabilities_brl

            # Get the exchange rate used for this date
            rate = currency_service.client.get_quotation(target_currency, ref_date)
            exchange_rate = float(rate) if rate else None
        else:
            total_assets = total_assets_brl
            current_liabilities = current_liabilities_brl
            exchange_rate = None

        net_worth = total_assets - current_liabilities
        evolution.append({
            "date": ref_date.isoformat(),
            "total_assets": float(total_assets),
            "total_liabilities": float(current_liabilities),
            "net_worth": float(net_worth),
            "exchange_rate": exchange_rate,
        })

    # Calculate variation if we have at least 2 data points
    variation = None
    variation_pct = None
    if len(evolution) >= 2:
        first_value = evolution[0]["net_worth"]
        last_value = evolution[-1]["net_worth"]
        variation = last_value - first_value
        if first_value != 0:
            variation_pct = (variation / first_value) * 100

    return {
        "client_id": client.id,
        "currency": target_currency,
        "period_months": months,
        "data_points": len(evolution),
        "variation": float(variation) if variation is not None else None,
        "variation_pct": float(variation_pct) if variation_pct is not None else None,
        "evolution": evolution,
    }


@router.get("/report/pdf")
def get_my_report_pdf(
    current_user: Annotated[User, Depends(get_client_user)],
    db: Annotated[Session, Depends(get_db)],
):
    """Generate PDF report for the client.

    Returns PDF file with patrimony summary.
    """
    from datetime import datetime
    from fastapi.responses import Response

    client = get_client_profile(current_user, db)

    # Get assets grouped by category
    assets = db.execute(
        select(PatAsset)
        .where(PatAsset.client_id == client.id)
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
        .where(PatLiability.client_id == client.id)
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
                "Content-Disposition": f"attachment; filename=meu_relatorio_{datetime.now().strftime('%Y%m%d')}.pdf"
            }
        )
    except ImportError:
        # Fallback: return HTML if weasyprint not available
        return Response(
            content=html_content.encode("utf-8"),
            media_type="text/html",
            headers={
                "Content-Disposition": f"attachment; filename=meu_relatorio_{datetime.now().strftime('%Y%m%d')}.html"
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
