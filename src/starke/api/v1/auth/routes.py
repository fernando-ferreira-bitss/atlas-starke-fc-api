"""Authentication routes for API v1."""

import os
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status, BackgroundTasks
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from starke.api.dependencies.database import get_db
from starke.api.dependencies.auth import (
    get_current_active_user,
    get_permission_service,
    ImpersonationContext,
)
from starke.api.v1.auth.schemas import (
    Token,
    UserMe,
    UserMeResponse,
    ChangePassword,
    ForgotPassword,
    ResetPassword,
    ForgotPasswordResponse,
    ProfileUpdate,
    UserPreferences,
    ImpersonationInfo,
)
from starke.domain.services.auth_service import AuthService
from starke.domain.services.permission_service import PermissionService
from starke.infrastructure.database.models import User
from starke.infrastructure.email.email_service import EmailService
from starke.core.logging import get_logger

router = APIRouter()
logger = get_logger(__name__)


@router.post("/login", response_model=Token)
def login(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    db: Annotated[Session, Depends(get_db)],
) -> Token:
    """Authenticate user and return JWT token.

    Uses OAuth2 password flow:
    - username: user's email
    - password: user's password
    """
    auth_service = AuthService(db)
    user = auth_service.authenticate_user(form_data.username, form_data.password)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User is inactive",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token = auth_service.create_access_token(data={"sub": user.email})

    return Token(access_token=access_token)


@router.get("/me", response_model=UserMeResponse)
def get_current_user_info(
    request: Request,
    current_user: Annotated[User, Depends(get_current_active_user)],
    permission_service: Annotated[PermissionService, Depends(get_permission_service)],
) -> UserMeResponse:
    """Get current authenticated user information.

    Returns user data along with their permissions and preferences.
    If in impersonation mode, includes impersonation context.
    """
    permissions = permission_service.get_user_permissions(current_user)

    # Parse preferences from JSON
    prefs = None
    if current_user.preferences:
        prefs = UserPreferences(**current_user.preferences)
    else:
        prefs = UserPreferences()  # Return defaults

    # Check for impersonation context
    impersonation_info = None
    if hasattr(request.state, "impersonation_context"):
        ctx: ImpersonationContext = request.state.impersonation_context
        impersonation_info = ImpersonationInfo(
            active=True,
            actor_email=ctx.actor_email,
            actor_role=ctx.actor_role,
            read_only=ctx.is_read_only,
        )

    return UserMeResponse(
        id=current_user.id,
        email=current_user.email,
        full_name=current_user.full_name,
        role=current_user.role,
        is_active=current_user.is_active,
        permissions=list(permissions),
        preferences=prefs,
        impersonation=impersonation_info,
    )


def _check_impersonation_readonly(request: Request) -> None:
    """Verifica se está em modo impersonation read-only e bloqueia a operação."""
    if hasattr(request.state, "impersonation_context"):
        ctx = request.state.impersonation_context
        if ctx.is_read_only:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Operação não permitida durante visualização como cliente. "
                "Encerre a sessão de impersonation para realizar alterações.",
            )


@router.put("/me", response_model=UserMeResponse)
def update_current_user_profile(
    request: Request,
    profile_data: ProfileUpdate,
    current_user: Annotated[User, Depends(get_current_active_user)],
    permission_service: Annotated[PermissionService, Depends(get_permission_service)],
    db: Annotated[Session, Depends(get_db)],
) -> UserMeResponse:
    """Update current user's profile (name and email).

    Users can only update their own profile.
    Blocked during impersonation mode.
    """
    _check_impersonation_readonly(request)
    auth_service = AuthService(db)

    # Update email if provided
    if profile_data.email is not None and profile_data.email != current_user.email:
        # Check if email is already taken
        existing = auth_service.get_user_by_email(profile_data.email)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered",
            )
        current_user.email = profile_data.email

    # Update full_name if provided
    if profile_data.full_name is not None:
        current_user.full_name = profile_data.full_name

    db.commit()
    db.refresh(current_user)

    # Return updated user info
    permissions = permission_service.get_user_permissions(current_user)
    prefs = UserPreferences(**(current_user.preferences or {}))

    return UserMeResponse(
        id=current_user.id,
        email=current_user.email,
        full_name=current_user.full_name,
        role=current_user.role,
        is_active=current_user.is_active,
        permissions=list(permissions),
        preferences=prefs,
    )


@router.get("/me/preferences", response_model=UserPreferences)
def get_current_user_preferences(
    current_user: Annotated[User, Depends(get_current_active_user)],
) -> UserPreferences:
    """Get current user's preferences.

    Returns default values if preferences are not set.
    """
    if current_user.preferences:
        return UserPreferences(**current_user.preferences)
    return UserPreferences()  # Return defaults


@router.put("/me/preferences", response_model=UserPreferences)
def update_current_user_preferences(
    request: Request,
    preferences: UserPreferences,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[Session, Depends(get_db)],
) -> UserPreferences:
    """Update current user's preferences.

    Replaces all preferences with the provided values.
    Blocked during impersonation mode.
    """
    _check_impersonation_readonly(request)

    current_user.preferences = preferences.model_dump()
    db.commit()
    db.refresh(current_user)

    return preferences


@router.post("/change-password", status_code=status.HTTP_204_NO_CONTENT)
def change_password(
    request: Request,
    password_data: ChangePassword,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[Session, Depends(get_db)],
) -> None:
    """Change current user's password.

    Requires current password for verification.
    Blocked during impersonation mode.
    """
    _check_impersonation_readonly(request)

    auth_service = AuthService(db)

    # Verify current password
    if not auth_service.verify_password(
        password_data.current_password, current_user.hashed_password
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect",
        )

    # Update password
    current_user.hashed_password = auth_service.get_password_hash(
        password_data.new_password
    )
    db.commit()


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(
    current_user: Annotated[User, Depends(get_current_active_user)],
) -> None:
    """Logout current user.

    Note: With JWT tokens, logout is typically handled client-side
    by discarding the token. This endpoint is provided for API completeness.
    """
    # JWT tokens are stateless, so no server-side action needed
    # In a future implementation, we could add token blacklisting
    pass


def send_password_reset_email(email: str, token: str, user_name: str) -> None:
    """Send password reset email in background."""
    try:
        email_service = EmailService()

        # Get frontend URL from environment or use default
        frontend_url = os.getenv("FRONTEND_URL", "http://localhost:3000")
        reset_link = f"{frontend_url}/reset-password?token={token}"

        html_body = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <title>Redefinição de Senha</title>
        </head>
        <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
            <div style="background: linear-gradient(135deg, #0066cc 0%, #004499 100%); padding: 30px; text-align: center; border-radius: 8px 8px 0 0;">
                <h1 style="color: white; margin: 0;">Starke</h1>
                <p style="color: rgba(255,255,255,0.9); margin: 10px 0 0 0;">Sistema de Gestão Patrimonial</p>
            </div>

            <div style="background: #f9f9f9; padding: 30px; border: 1px solid #e0e0e0; border-top: none;">
                <h2 style="color: #333; margin-top: 0;">Olá, {user_name}!</h2>

                <p style="color: #555; line-height: 1.6;">
                    Recebemos uma solicitação para redefinir a senha da sua conta.
                    Clique no botão abaixo para criar uma nova senha:
                </p>

                <div style="text-align: center; margin: 30px 0;">
                    <a href="{reset_link}"
                       style="background: #0066cc; color: white; padding: 14px 30px;
                              text-decoration: none; border-radius: 6px; font-weight: bold;
                              display: inline-block;">
                        Redefinir Minha Senha
                    </a>
                </div>

                <p style="color: #888; font-size: 14px; line-height: 1.6;">
                    Este link é válido por <strong>1 hora</strong>. Se você não solicitou
                    a redefinição de senha, ignore este email.
                </p>

                <hr style="border: none; border-top: 1px solid #e0e0e0; margin: 25px 0;">

                <p style="color: #999; font-size: 12px; margin: 0;">
                    Se o botão não funcionar, copie e cole o link abaixo no seu navegador:
                </p>
                <p style="color: #0066cc; font-size: 12px; word-break: break-all;">
                    {reset_link}
                </p>
            </div>

            <div style="background: #333; padding: 20px; text-align: center; border-radius: 0 0 8px 8px;">
                <p style="color: #999; font-size: 12px; margin: 0;">
                    © 2025 Starke - Todos os direitos reservados
                </p>
            </div>
        </body>
        </html>
        """

        email_service.send_html_email(
            recipients=[{"name": user_name, "email": email}],
            subject="Redefinição de Senha - Starke",
            html_body=html_body,
        )
        logger.info("Password reset email sent", email=email)
    except Exception as e:
        logger.error("Failed to send password reset email", email=email, error=str(e))


@router.post("/forgot-password", response_model=ForgotPasswordResponse)
def forgot_password(
    data: ForgotPassword,
    background_tasks: BackgroundTasks,
    db: Annotated[Session, Depends(get_db)],
) -> ForgotPasswordResponse:
    """Request password reset.

    Sends an email with a reset link if the email exists.
    Always returns success to prevent email enumeration.
    """
    auth_service = AuthService(db)
    user = auth_service.get_user_by_email(data.email)

    if user and user.is_active:
        # Generate reset token
        token = auth_service.create_password_reset_token(user.email)

        # Send email in background
        background_tasks.add_task(
            send_password_reset_email,
            user.email,
            token,
            user.full_name,
        )
        logger.info("Password reset requested", email=data.email)
    else:
        # Log but don't reveal if user exists
        logger.warning("Password reset requested for unknown/inactive email", email=data.email)

    # Always return success to prevent email enumeration
    return ForgotPasswordResponse(
        message="Se o email estiver cadastrado, você receberá um link para redefinir sua senha."
    )


@router.post("/reset-password", status_code=status.HTTP_204_NO_CONTENT)
def reset_password(
    data: ResetPassword,
    db: Annotated[Session, Depends(get_db)],
) -> None:
    """Reset password using token.

    Validates the token and updates the password.
    """
    # Verify token
    email = AuthService.verify_password_reset_token(data.token)

    if not email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Token inválido ou expirado",
        )

    # Reset password
    auth_service = AuthService(db)
    success = auth_service.reset_password(email, data.new_password)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Não foi possível redefinir a senha",
        )

    logger.info("Password reset successful", email=email)
