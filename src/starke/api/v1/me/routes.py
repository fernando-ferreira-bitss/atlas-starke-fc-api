"""User profile routes for API v1.

These endpoints are for users to view and manage their own profile.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from starke.api.dependencies.database import get_db
from starke.api.dependencies.auth import get_current_user
from starke.api.v1.auth.schemas import UserPreferences
from starke.infrastructure.database.models import User

router = APIRouter()


@router.get("/profile")
def get_my_profile(
    current_user: Annotated[User, Depends(get_current_user)],
) -> dict:
    """Get current user's profile.

    Returns basic user information.
    """
    return {
        "id": current_user.id,
        "email": current_user.email,
        "full_name": current_user.full_name,
        "role": current_user.role,
        "is_active": current_user.is_active,
        "preferences": current_user.preferences,
        "created_at": current_user.created_at.isoformat() if current_user.created_at else None,
    }


@router.put("/preferences")
def update_my_preferences(
    preferences: UserPreferences,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> dict:
    """Update current user's preferences.

    Allows users to set their display preferences like default currency,
    timezone, date format, etc.
    """
    current_user.preferences = preferences.model_dump()
    db.commit()
    db.refresh(current_user)

    return {
        "message": "Preferences updated successfully",
        "preferences": current_user.preferences,
    }
