"""Document routes with file upload support."""

import os
from datetime import datetime
from io import BytesIO
from typing import Optional
from uuid import uuid4

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse, StreamingResponse
from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

from starke.api.dependencies import get_db
from starke.api.dependencies.auth import get_current_user, require_permission
from starke.core.storage import get_storage
from starke.domain.permissions.screens import Screen
from starke.infrastructure.database.models import User, UserRole
from starke.infrastructure.database.patrimony.document import PatDocument
from starke.infrastructure.database.patrimony.client import PatClient
from starke.infrastructure.database.patrimony.account import PatAccount
from starke.infrastructure.database.patrimony.asset import PatAsset

from .schemas import (
    DocumentListResponse,
    DocumentResponse,
    DocumentUpdate,
    DocumentUploadError,
    DocumentValidate,
    MultipleUploadResponse,
)

router = APIRouter(prefix="/documents", tags=["Documents"])

# Configuration
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
ALLOWED_EXTENSIONS = {".pdf", ".png", ".jpg", ".jpeg", ".xls", ".xlsx", ".csv", ".doc", ".docx"}
ALLOWED_MIME_TYPES = {
    "application/pdf",
    "image/png",
    "image/jpeg",
    "application/vnd.ms-excel",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "text/csv",
    "application/msword",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
}


def get_storage_key(client_id: str, document_type: str, filename: str) -> str:
    """Generate storage key for document."""
    # Key structure: {client_id}/{type}/{filename}
    return f"{client_id}/{document_type}/{filename}"


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


def build_document_response(doc: PatDocument) -> DocumentResponse:
    """Build document response with related data."""
    return DocumentResponse(
        id=doc.id,
        client_id=doc.client_id,
        client_name=doc.client.name if doc.client else None,
        account_id=doc.account_id,
        asset_id=doc.asset_id,
        document_type=doc.document_type,
        title=doc.title,
        description=doc.description,
        file_name=doc.file_name,
        s3_key=doc.s3_key,
        file_size=doc.file_size,
        mime_type=doc.mime_type,
        reference_date=doc.reference_date,
        uploaded_by=doc.uploaded_by,
        uploader_name=doc.uploader.full_name if doc.uploader else None,
        # Status fields
        status=doc.status,
        validated_by=doc.validated_by,
        validator_name=doc.validator.full_name if doc.validator else None,
        validated_at=doc.validated_at,
        validation_notes=doc.validation_notes,
        # Timestamps
        created_at=doc.created_at,
        updated_at=doc.updated_at,
    )


@router.post("/upload", response_model=DocumentResponse, status_code=201)
async def upload_document(
    file: UploadFile = File(...),
    client_id: str = Form(...),
    document_type: str = Form(...),
    title: str = Form(...),
    description: Optional[str] = Form(None),
    reference_date: Optional[str] = Form(None),
    account_id: Optional[str] = Form(None),
    asset_id: Optional[str] = Form(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Screen.DOCUMENTS)),
):
    """Upload a document for a client.

    Supported types: contract, report, statement, certificate, proof, other
    Max file size: 10MB
    Allowed formats: PDF, PNG, JPG, XLS, XLSX, CSV, DOC, DOCX
    """
    # Validate document type
    valid_types = {"contract", "report", "statement", "certificate", "proof", "other"}
    if document_type not in valid_types:
        raise HTTPException(
            status_code=400,
            detail=f"Tipo de documento inválido. Valores permitidos: {', '.join(valid_types)}",
        )

    # Check client access
    client = check_client_access(client_id, current_user, db)

    # Validate file extension
    if file.filename:
        ext = os.path.splitext(file.filename)[1].lower()
        if ext not in ALLOWED_EXTENSIONS:
            raise HTTPException(
                status_code=400,
                detail=f"Extensão não permitida. Permitidas: {', '.join(ALLOWED_EXTENSIONS)}",
            )

    # Validate MIME type
    if file.content_type and file.content_type not in ALLOWED_MIME_TYPES:
        raise HTTPException(
            status_code=400,
            detail="Tipo de arquivo não permitido",
        )

    # Read file and check size
    content = await file.read()
    file_size = len(content)
    if file_size > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=413,
            detail=f"Arquivo excede o tamanho máximo de {MAX_FILE_SIZE // (1024 * 1024)}MB",
        )

    # Validate account if provided
    if account_id:
        account = db.get(PatAccount, account_id)
        if not account or account.client_id != client_id:
            raise HTTPException(status_code=400, detail="Conta não encontrada")

    # Validate asset if provided
    if asset_id:
        asset = db.get(PatAsset, asset_id)
        if not asset or asset.client_id != client_id:
            raise HTTPException(status_code=400, detail="Ativo não encontrado")

    # Generate unique filename
    original_filename = file.filename or "document"
    ext = os.path.splitext(original_filename)[1].lower()
    unique_filename = f"{uuid4()}{ext}"

    # Upload file using storage service
    storage = get_storage()
    storage_key = get_storage_key(client_id, document_type, unique_filename)
    storage.upload(content, storage_key, file.content_type)

    # Parse reference date
    ref_date = None
    if reference_date:
        try:
            ref_date = datetime.fromisoformat(reference_date.replace("Z", "+00:00"))
        except ValueError:
            pass

    # Create document record
    doc = PatDocument(
        id=str(uuid4()),
        client_id=client_id,
        account_id=account_id,
        asset_id=asset_id,
        document_type=document_type,
        title=title,
        description=description,
        file_name=original_filename,
        s3_key=storage_key,  # Storage key (works for both S3 and local)
        file_size=file_size,
        mime_type=file.content_type,
        reference_date=ref_date,
        uploaded_by=current_user.id,
    )
    db.add(doc)
    db.commit()

    # Reload with relationships
    doc = db.execute(
        select(PatDocument)
        .options(
            joinedload(PatDocument.client),
            joinedload(PatDocument.uploader),
            joinedload(PatDocument.validator),
        )
        .where(PatDocument.id == doc.id)
    ).unique().scalar_one()

    return build_document_response(doc)


@router.post("/upload-multiple", response_model=MultipleUploadResponse, status_code=201)
async def upload_multiple_documents(
    files: list[UploadFile] = File(...),
    client_id: str = Form(...),
    document_type: str = Form(...),
    description: Optional[str] = Form(None),
    reference_date: Optional[str] = Form(None),
    account_id: Optional[str] = Form(None),
    asset_id: Optional[str] = Form(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Screen.DOCUMENTS)),
):
    """Upload multiple documents for a client.

    Each file will be uploaded with the same metadata (type, description, etc.)
    but will have its original filename as the title.

    Supported types: contract, report, statement, certificate, proof, other
    Max file size: 10MB per file
    Allowed formats: PDF, PNG, JPG, XLS, XLSX, CSV, DOC, DOCX
    """
    # Validate document type
    valid_types = {"contract", "report", "statement", "certificate", "proof", "other"}
    if document_type not in valid_types:
        raise HTTPException(
            status_code=400,
            detail=f"Tipo de documento inválido. Valores permitidos: {', '.join(valid_types)}",
        )

    # Check client access
    check_client_access(client_id, current_user, db)

    # Validate account if provided
    if account_id:
        account = db.get(PatAccount, account_id)
        if not account or account.client_id != client_id:
            raise HTTPException(status_code=400, detail="Conta não encontrada")

    # Validate asset if provided
    if asset_id:
        asset = db.get(PatAsset, asset_id)
        if not asset or asset.client_id != client_id:
            raise HTTPException(status_code=400, detail="Ativo não encontrado")

    # Parse reference date once
    ref_date = None
    if reference_date:
        try:
            ref_date = datetime.fromisoformat(reference_date.replace("Z", "+00:00"))
        except ValueError:
            pass

    uploaded_docs: list[DocumentResponse] = []
    errors: list[DocumentUploadError] = []
    storage = get_storage()

    for file in files:
        original_filename = file.filename or "document"

        try:
            # Validate file extension
            ext = os.path.splitext(original_filename)[1].lower()
            if ext not in ALLOWED_EXTENSIONS:
                errors.append(DocumentUploadError(
                    file_name=original_filename,
                    error=f"Extensão não permitida. Permitidas: {', '.join(ALLOWED_EXTENSIONS)}"
                ))
                continue

            # Validate MIME type
            if file.content_type and file.content_type not in ALLOWED_MIME_TYPES:
                errors.append(DocumentUploadError(
                    file_name=original_filename,
                    error="Tipo de arquivo não permitido"
                ))
                continue

            # Read file and check size
            content = await file.read()
            file_size = len(content)
            if file_size > MAX_FILE_SIZE:
                errors.append(DocumentUploadError(
                    file_name=original_filename,
                    error=f"Arquivo excede o tamanho máximo de {MAX_FILE_SIZE // (1024 * 1024)}MB"
                ))
                continue

            # Generate unique filename
            unique_filename = f"{uuid4()}{ext}"

            # Upload file using storage service
            storage_key = get_storage_key(client_id, document_type, unique_filename)
            storage.upload(content, storage_key, file.content_type)

            # Use filename (without extension) as title
            title = os.path.splitext(original_filename)[0]

            # Create document record
            doc = PatDocument(
                id=str(uuid4()),
                client_id=client_id,
                account_id=account_id,
                asset_id=asset_id,
                document_type=document_type,
                title=title,
                description=description,
                file_name=original_filename,
                s3_key=storage_key,
                file_size=file_size,
                mime_type=file.content_type,
                reference_date=ref_date,
                uploaded_by=current_user.id,
            )
            db.add(doc)
            db.flush()  # Get the ID

            # Reload with relationships
            doc = db.execute(
                select(PatDocument)
                .options(
                    joinedload(PatDocument.client),
                    joinedload(PatDocument.uploader),
                    joinedload(PatDocument.validator),
                )
                .where(PatDocument.id == doc.id)
            ).unique().scalar_one()

            uploaded_docs.append(build_document_response(doc))

        except Exception as e:
            errors.append(DocumentUploadError(
                file_name=original_filename,
                error=str(e)
            ))

    # Commit all successful uploads
    db.commit()

    return MultipleUploadResponse(
        uploaded=uploaded_docs,
        errors=errors,
        total_files=len(files),
        success_count=len(uploaded_docs),
        error_count=len(errors),
    )


@router.get("", response_model=DocumentListResponse)
def list_documents(
    page: int = Query(1, ge=1, description="Página"),
    per_page: int = Query(20, ge=1, le=100, description="Itens por página"),
    client_id: Optional[str] = Query(None, description="Filtrar por cliente"),
    document_type: Optional[str] = Query(None, description="Filtrar por tipo"),
    status: Optional[str] = Query(None, description="Filtrar por status: pending, validated, rejected"),
    start_date: Optional[str] = Query(None, description="Data inicial (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="Data final (YYYY-MM-DD)"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Screen.DOCUMENTS)),
):
    """List all documents with pagination and filters."""
    query = select(PatDocument).options(
        joinedload(PatDocument.client),
        joinedload(PatDocument.uploader),
        joinedload(PatDocument.validator),
    )

    # Access control
    if current_user.role == UserRole.CLIENT.value:
        client = db.execute(
            select(PatClient).where(PatClient.user_id == current_user.id)
        ).scalar_one_or_none()
        if client:
            query = query.where(PatDocument.client_id == client.id)
        else:
            query = query.where(False)
    elif current_user.role == UserRole.RM.value:
        client_ids = db.execute(
            select(PatClient.id).where(PatClient.rm_user_id == current_user.id)
        ).scalars().all()
        query = query.where(PatDocument.client_id.in_(client_ids))

    # Apply filters
    if client_id:
        query = query.where(PatDocument.client_id == client_id)
    if document_type:
        query = query.where(PatDocument.document_type == document_type)
    if status:
        query = query.where(PatDocument.status == status)
    if start_date:
        try:
            start = datetime.strptime(start_date, "%Y-%m-%d")
            query = query.where(PatDocument.created_at >= start)
        except ValueError:
            pass
    if end_date:
        try:
            end = datetime.strptime(end_date, "%Y-%m-%d")
            query = query.where(PatDocument.created_at <= end)
        except ValueError:
            pass

    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total = db.execute(count_query).scalar() or 0

    # Pagination
    offset = (page - 1) * per_page
    query = query.order_by(PatDocument.created_at.desc()).offset(offset).limit(per_page)

    items = db.execute(query).unique().scalars().all()

    return DocumentListResponse(
        items=[build_document_response(doc) for doc in items],
        total=total,
        page=page,
        per_page=per_page,
        pages=(total + per_page - 1) // per_page if total > 0 else 0,
    )


@router.get("/{document_id}", response_model=DocumentResponse)
def get_document(
    document_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Screen.DOCUMENTS)),
):
    """Get document by ID."""
    doc = db.execute(
        select(PatDocument)
        .options(
            joinedload(PatDocument.client),
            joinedload(PatDocument.uploader),
            joinedload(PatDocument.validator),
        )
        .where(PatDocument.id == document_id)
    ).unique().scalar_one_or_none()

    if not doc:
        raise HTTPException(status_code=404, detail="Documento não encontrado")

    # Check access
    check_client_access(doc.client_id, current_user, db)

    return build_document_response(doc)


@router.get("/{document_id}/download")
def download_document(
    document_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Screen.DOCUMENTS)),
):
    """Download document file."""
    doc = db.get(PatDocument, document_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Documento não encontrado")

    # Check access
    check_client_access(doc.client_id, current_user, db)

    storage = get_storage()

    # Check file exists
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


@router.put("/{document_id}", response_model=DocumentResponse)
def update_document(
    document_id: str,
    data: DocumentUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Screen.DOCUMENTS)),
):
    """Update document metadata."""
    doc = db.get(PatDocument, document_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Documento não encontrado")

    # Check access
    check_client_access(doc.client_id, current_user, db)

    # Update fields
    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(doc, field, value)

    db.commit()

    # Reload with relationships
    doc = db.execute(
        select(PatDocument)
        .options(
            joinedload(PatDocument.client),
            joinedload(PatDocument.uploader),
            joinedload(PatDocument.validator),
        )
        .where(PatDocument.id == doc.id)
    ).unique().scalar_one()

    return build_document_response(doc)


@router.delete("/{document_id}", status_code=204)
def delete_document(
    document_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Screen.DOCUMENTS)),
):
    """Delete document and file."""
    doc = db.get(PatDocument, document_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Documento não encontrado")

    # Check access
    check_client_access(doc.client_id, current_user, db)

    # Delete file from storage
    storage = get_storage()
    storage.delete(doc.s3_key)

    # Delete record
    db.delete(doc)
    db.commit()

    return None


@router.put("/{document_id}/validate", response_model=DocumentResponse)
def validate_document(
    document_id: str,
    data: DocumentValidate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Screen.DOCUMENTS)),
):
    """Validate or reject a document.

    Only admin and rm roles can validate documents.
    """
    # Only admin and rm can validate
    if current_user.role not in [UserRole.ADMIN.value, UserRole.RM.value]:
        raise HTTPException(
            status_code=403,
            detail="Apenas administradores e RMs podem validar documentos"
        )

    doc = db.get(PatDocument, document_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Documento não encontrado")

    # Check access
    check_client_access(doc.client_id, current_user, db)

    # Update validation status
    doc.status = data.status
    doc.validation_notes = data.validation_notes

    if data.status in ["validated", "rejected"]:
        doc.validated_by = current_user.id
        doc.validated_at = datetime.utcnow()
    else:
        # If setting back to pending, clear validation info
        doc.validated_by = None
        doc.validated_at = None

    db.commit()

    # Reload with relationships
    doc = db.execute(
        select(PatDocument)
        .options(
            joinedload(PatDocument.client),
            joinedload(PatDocument.uploader),
            joinedload(PatDocument.validator),
        )
        .where(PatDocument.id == doc.id)
    ).unique().scalar_one()

    return build_document_response(doc)
