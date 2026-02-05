"""Document schemas."""

from datetime import datetime
from typing import Optional, Literal
from pydantic import BaseModel, ConfigDict, Field


# Status types
DocumentStatus = Literal["pending", "validated", "rejected"]


class DocumentBase(BaseModel):
    """Base document schema."""

    document_type: str  # contract, report, statement, certificate, proof, other
    title: str
    description: Optional[str] = None
    reference_date: Optional[datetime] = None


class DocumentCreate(DocumentBase):
    """Schema for creating a document (metadata only, file is uploaded separately)."""

    client_id: str
    account_id: Optional[str] = None
    asset_id: Optional[str] = None


class DocumentUpdate(BaseModel):
    """Schema for updating a document."""

    title: Optional[str] = None
    description: Optional[str] = None
    document_type: Optional[str] = None
    reference_date: Optional[datetime] = None


class DocumentValidate(BaseModel):
    """Schema for validating/rejecting a document."""

    status: DocumentStatus = Field(..., description="Status: pending, validated, rejected")
    validation_notes: Optional[str] = Field(None, description="Notas da validação")


class DocumentResponse(DocumentBase):
    """Document response schema."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    client_id: str
    client_name: Optional[str] = None
    account_id: Optional[str] = None
    asset_id: Optional[str] = None
    file_name: str
    s3_key: str
    file_size: Optional[int] = None
    mime_type: Optional[str] = None
    uploaded_by: Optional[int] = None
    uploader_name: Optional[str] = None
    # Status fields
    status: str = "pending"
    validated_by: Optional[int] = None
    validator_name: Optional[str] = None
    validated_at: Optional[datetime] = None
    validation_notes: Optional[str] = None
    # Timestamps
    created_at: datetime
    updated_at: Optional[datetime] = None


class DocumentListResponse(BaseModel):
    """Paginated document list response."""

    items: list[DocumentResponse]
    total: int
    page: int
    per_page: int
    pages: int


class DocumentUploadError(BaseModel):
    """Error for a single file upload failure."""

    file_name: str
    error: str


class MultipleUploadResponse(BaseModel):
    """Response for multiple file upload."""

    uploaded: list[DocumentResponse]
    errors: list[DocumentUploadError]
    total_files: int
    success_count: int
    error_count: int
