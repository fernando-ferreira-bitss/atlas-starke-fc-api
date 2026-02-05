"""Pydantic schemas for authentication endpoints."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, Field, model_validator


class Token(BaseModel):
    """JWT token response."""

    access_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    """Token payload data."""

    email: Optional[str] = None


class UserBase(BaseModel):
    """Base user schema."""

    email: EmailStr
    full_name: str = Field(..., min_length=1, max_length=255)


class UserCreate(UserBase):
    """Schema for creating a new user."""

    password: str = Field(..., min_length=6, max_length=100)
    role: str = Field(default="analyst", pattern="^(admin|rm|analyst|client)$")
    client_id: Optional[str] = Field(
        None,
        description="ID do cliente (obrigatório quando role=client)"
    )

    @model_validator(mode="after")
    def validate_client_for_client_role(self):
        """Validate that client_id is provided when role is client."""
        if self.role == "client" and not self.client_id:
            raise ValueError("client_id é obrigatório quando role=client")
        if self.role != "client" and self.client_id:
            raise ValueError("client_id só pode ser informado quando role=client")
        return self


class UserUpdate(BaseModel):
    """Schema for updating a user."""

    email: Optional[EmailStr] = None
    full_name: Optional[str] = Field(None, min_length=1, max_length=255)
    password: Optional[str] = Field(None, min_length=6, max_length=100)
    role: Optional[str] = Field(None, pattern="^(admin|rm|analyst|client)$")
    is_active: Optional[bool] = None
    client_id: Optional[str] = Field(
        None,
        description="ID do cliente (obrigatório quando role=client)"
    )


class UserResponse(UserBase):
    """User response schema."""

    id: int
    role: str
    is_active: bool
    is_superuser: bool
    client_id: Optional[str] = None
    client_name: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class UserMe(UserBase):
    """Current user info (for /me endpoint)."""

    id: int
    role: str
    is_active: bool
    permissions: list[str] = []

    model_config = {"from_attributes": True}


class ChangePassword(BaseModel):
    """Schema for changing password."""

    current_password: str
    new_password: str = Field(..., min_length=6, max_length=100)


class ForgotPassword(BaseModel):
    """Schema for forgot password request."""

    email: EmailStr


class ResetPassword(BaseModel):
    """Schema for resetting password with token."""

    token: str
    new_password: str = Field(..., min_length=6, max_length=100)


class ForgotPasswordResponse(BaseModel):
    """Response for forgot password request."""

    message: str


class ProfileUpdate(BaseModel):
    """Schema for updating user's own profile."""

    full_name: Optional[str] = Field(None, min_length=1, max_length=255)
    email: Optional[EmailStr] = None


class UserPreferences(BaseModel):
    """Schema for user preferences."""

    default_currency: str = Field(default="BRL", max_length=3)
    theme: str = Field(default="light", pattern="^(light|dark)$")


class ImpersonationInfo(BaseModel):
    """Informações de impersonation para o endpoint /me."""

    active: bool = True
    actor_email: str
    actor_role: str
    read_only: bool = True


class UserMeResponse(UserBase):
    """Extended user info with preferences (for /me endpoint)."""

    id: int
    role: str
    is_active: bool
    permissions: list[str] = []
    preferences: Optional[UserPreferences] = None
    impersonation: Optional[ImpersonationInfo] = None

    model_config = {"from_attributes": True}


class UserListResponse(BaseModel):
    """Schema for paginated user list response."""

    items: list[UserResponse]
    total: int
    page: int
    per_page: int
    pages: int
