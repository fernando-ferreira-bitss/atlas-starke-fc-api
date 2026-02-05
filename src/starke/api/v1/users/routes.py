"""Users management routes for API v1."""

from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from starke.api.dependencies.database import get_db
from starke.api.dependencies.auth import require_permission
from sqlalchemy import func

from starke.api.v1.auth.schemas import UserCreate, UserUpdate, UserResponse, UserListResponse
from starke.domain.permissions.screens import Screen
from starke.domain.services.auth_service import AuthService
from starke.infrastructure.database.models import User, UserRole

router = APIRouter()


def _build_user_response(user: User) -> UserResponse:
    """Build UserResponse."""
    return UserResponse(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        role=user.role,
        is_active=user.is_active,
        is_superuser=user.is_superuser,
        client_id=None,
        client_name=None,
        created_at=user.created_at,
        updated_at=user.updated_at,
    )


@router.get("", response_model=UserListResponse)
def list_users(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_permission(Screen.USERS))],
    page: int = Query(1, ge=1, description="Página"),
    per_page: int = Query(20, ge=1, le=100, description="Itens por página"),
    role: Optional[str] = Query(None, pattern="^(admin|rm|analyst|client)$"),
    is_active: Optional[bool] = None,
    search: Optional[str] = Query(None, description="Buscar por nome ou email"),
) -> UserListResponse:
    """List all users with pagination and optional filters.

    Requires USERS permission.
    """
    query = db.query(User)

    if role:
        query = query.filter(User.role == role)

    if is_active is not None:
        query = query.filter(User.is_active == is_active)

    if search:
        search_filter = f"%{search}%"
        query = query.filter(
            (User.full_name.ilike(search_filter)) | (User.email.ilike(search_filter))
        )

    # Count total
    total = query.count()

    # Pagination
    offset = (page - 1) * per_page
    items = query.order_by(User.created_at.desc()).offset(offset).limit(per_page).all()

    return UserListResponse(
        items=[_build_user_response(user) for user in items],
        total=total,
        page=page,
        per_page=per_page,
        pages=(total + per_page - 1) // per_page if total > 0 else 0,
    )


@router.post("", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def create_user(
    user_data: UserCreate,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_permission(Screen.USERS_CREATE))],
) -> UserResponse:
    """Create a new user.

    Requires USERS_CREATE permission.
    """
    auth_service = AuthService(db)

    # Check if email already exists
    existing = auth_service.get_user_by_email(user_data.email)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )

    # Create user
    user = User(
        email=user_data.email,
        full_name=user_data.full_name,
        hashed_password=auth_service.get_password_hash(user_data.password),
        role=user_data.role,
        is_active=True,
        is_superuser=(user_data.role == UserRole.ADMIN.value),
    )

    db.add(user)
    db.commit()
    db.refresh(user)

    return _build_user_response(user)


@router.get("/{user_id}", response_model=UserResponse)
def get_user(
    user_id: int,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_permission(Screen.USERS))],
) -> UserResponse:
    """Get a specific user by ID.

    Requires USERS permission.
    """
    user = db.query(User).filter(User.id == user_id).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    return _build_user_response(user)


@router.put("/{user_id}", response_model=UserResponse)
def update_user(
    user_id: int,
    user_data: UserUpdate,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_permission(Screen.USERS_EDIT))],
) -> UserResponse:
    """Update a user.

    Requires USERS_EDIT permission.
    """
    user = db.query(User).filter(User.id == user_id).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    # Prevent non-admin from modifying admin users
    if user.is_admin and not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot modify admin users",
        )

    # Update fields
    if user_data.email is not None:
        # Check if new email is already taken
        existing = db.query(User).filter(
            User.email == user_data.email,
            User.id != user_id,
        ).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered",
            )
        user.email = user_data.email

    if user_data.full_name is not None:
        user.full_name = user_data.full_name

    if user_data.role is not None:
        # Only admin can change roles
        if not current_user.is_admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only admin can change user roles",
            )
        user.role = user_data.role
        user.is_superuser = (user_data.role == UserRole.ADMIN.value)

    if user_data.is_active is not None:
        user.is_active = user_data.is_active

    if user_data.password is not None:
        auth_service = AuthService(db)
        user.hashed_password = auth_service.get_password_hash(user_data.password)

    db.commit()
    db.refresh(user)

    return _build_user_response(user)


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(
    user_id: int,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_permission(Screen.USERS_DELETE))],
) -> None:
    """Soft delete a user (set is_active=False).

    Requires USERS_DELETE permission.
    """
    user = db.query(User).filter(User.id == user_id).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    # Prevent deleting yourself
    if user.id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete yourself",
        )

    # Prevent non-admin from deleting admin users
    if user.is_admin and not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot delete admin users",
        )

    # Soft delete
    user.is_active = False
    db.commit()
