"""Authentication service for user management and JWT token generation."""

from datetime import datetime, timedelta, timezone
from typing import Optional

from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from starke.core.config import get_settings
from starke.infrastructure.database.models import User

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class AuthService:
    """Service for user authentication and authorization."""

    def __init__(self, db: Session):
        """Initialize auth service with database session."""
        self.db = db

    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        """Verify a password against its hash."""
        return pwd_context.verify(plain_password, hashed_password)

    @staticmethod
    def get_password_hash(password: str) -> str:
        """Hash a password for storing."""
        return pwd_context.hash(password)

    def authenticate_user(self, email: str, password: str) -> Optional[User]:
        """Authenticate a user by email and password."""
        user = self.db.query(User).filter(User.email == email).first()
        if not user:
            return None
        if not self.verify_password(password, user.hashed_password):
            return None
        if not user.is_active:
            return None
        return user

    def create_user(
        self,
        email: str,
        password: str,
        is_superuser: bool = False,
        is_active: bool = True,
        full_name: Optional[str] = None,
    ) -> User:
        """Create a new user."""
        # Check if user already exists
        existing_user = self.db.query(User).filter(User.email == email).first()
        if existing_user:
            raise ValueError(f"User with email {email} already exists")

        # If full_name not provided, use email username as fallback
        if not full_name:
            full_name = email.split('@')[0].title()

        hashed_password = self.get_password_hash(password)
        user = User(
            email=email,
            full_name=full_name,
            hashed_password=hashed_password,
            is_superuser=is_superuser,
            is_active=is_active,
        )
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        return user

    def get_user_by_email(self, email: str) -> Optional[User]:
        """Get user by email."""
        return self.db.query(User).filter(User.email == email).first()

    def get_user_by_id(self, user_id: int) -> Optional[User]:
        """Get user by ID."""
        return self.db.query(User).filter(User.id == user_id).first()

    def update_user(
        self,
        user_id: int,
        email: Optional[str] = None,
        password: Optional[str] = None,
        is_active: Optional[bool] = None,
        is_superuser: Optional[bool] = None,
    ) -> Optional[User]:
        """Update user information."""
        user = self.get_user_by_id(user_id)
        if not user:
            return None

        if email is not None:
            # Check if email is already taken by another user
            existing_user = self.db.query(User).filter(
                User.email == email, User.id != user_id
            ).first()
            if existing_user:
                raise ValueError(f"Email {email} is already taken")
            user.email = email

        if password is not None:
            user.hashed_password = self.get_password_hash(password)

        if is_active is not None:
            user.is_active = is_active

        if is_superuser is not None:
            user.is_superuser = is_superuser

        user.updated_at = datetime.now(timezone.utc)
        self.db.commit()
        self.db.refresh(user)
        return user

    def delete_user(self, user_id: int) -> bool:
        """Delete a user (soft delete by setting is_active to False)."""
        user = self.get_user_by_id(user_id)
        if not user:
            return False

        user.is_active = False
        user.updated_at = datetime.now(timezone.utc)
        self.db.commit()
        return True

    def deactivate_user(self, user_id: int) -> Optional[User]:
        """Deactivate a user (soft delete)."""
        return self.update_user(user_id, is_active=False)

    def activate_user(self, user_id: int) -> Optional[User]:
        """Activate a user."""
        return self.update_user(user_id, is_active=True)

    @staticmethod
    def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
        """Create JWT access token."""
        settings = get_settings()
        to_encode = data.copy()
        if expires_delta:
            expire = datetime.now(timezone.utc) + expires_delta
        else:
            expire = datetime.now(timezone.utc) + timedelta(
                minutes=settings.jwt_access_token_expire_minutes
            )

        to_encode.update({"exp": expire})
        encoded_jwt = jwt.encode(to_encode, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)
        return encoded_jwt

    @staticmethod
    def decode_access_token(token: str) -> Optional[dict]:
        """Decode and verify JWT access token."""
        settings = get_settings()
        try:
            payload = jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
            return payload
        except JWTError:
            return None

    @staticmethod
    def create_password_reset_token(email: str) -> str:
        """Create a password reset token valid for 1 hour."""
        settings = get_settings()
        expire = datetime.now(timezone.utc) + timedelta(hours=1)
        to_encode = {
            "sub": email,
            "exp": expire,
            "type": "password_reset",
        }
        encoded_jwt = jwt.encode(to_encode, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)
        return encoded_jwt

    @staticmethod
    def verify_password_reset_token(token: str) -> Optional[str]:
        """Verify password reset token and return email if valid."""
        settings = get_settings()
        try:
            payload = jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
            if payload.get("type") != "password_reset":
                return None
            email: str = payload.get("sub")
            return email
        except JWTError:
            return None

    def reset_password(self, email: str, new_password: str) -> bool:
        """Reset user password."""
        user = self.get_user_by_email(email)
        if not user:
            return False
        user.hashed_password = self.get_password_hash(new_password)
        user.updated_at = datetime.now(timezone.utc)
        self.db.commit()
        return True
