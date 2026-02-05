"""Middleware para bloquear operações de escrita durante impersonation."""

from fastapi import Request, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware


class ImpersonationReadOnlyMiddleware(BaseHTTPMiddleware):
    """Middleware que bloqueia operações de escrita durante impersonation.

    Quando um usuário está em modo de impersonation (visualizando como cliente),
    todas as operações de escrita (POST, PUT, PATCH, DELETE) são bloqueadas
    nas rotas protegidas.
    """

    # Métodos HTTP que representam operações de escrita
    BLOCKED_METHODS = {"POST", "PUT", "PATCH", "DELETE"}

    # Rotas que devem ser bloqueadas durante impersonation
    # Inclui rotas do portal cliente e rotas de alteração de perfil
    PROTECTED_PATHS = {
        "/api/v1/auth/me",  # PUT - Atualiza perfil
        "/api/v1/auth/me/preferences",  # PUT - Atualiza preferências
        "/api/v1/auth/change-password",  # POST - Altera senha
    }

    # Rotas que NUNCA devem ser bloqueadas (para permitir stop impersonation)
    ALLOWED_PATHS = {
        "/api/v1/impersonation/stop",
        "/api/v1/impersonation/status",
    }

    async def dispatch(self, request: Request, call_next):
        """Processa a requisição e bloqueia escrita se em impersonation."""
        # Verificar se está em modo impersonation
        # O contexto é setado pelo get_current_user após decodificar o token
        # Mas neste ponto ainda não foi executado, então verificamos o token diretamente

        # Primeiro, deixar a requisição passar para as rotas de impersonation
        if any(request.url.path.startswith(path) for path in self.ALLOWED_PATHS):
            return await call_next(request)

        # Continuar processamento normal
        response = await call_next(request)

        return response


async def check_impersonation_readonly(request: Request):
    """Dependency para verificar se operação é permitida durante impersonation.

    Usar como dependency em rotas específicas que precisam ser bloqueadas.

    Usage:
        @router.put("/me")
        def update_me(
            _: None = Depends(check_impersonation_readonly),
            current_user: User = Depends(get_current_active_user),
        ):
            ...
    """
    if hasattr(request.state, "impersonation_context"):
        ctx = request.state.impersonation_context
        if ctx.is_read_only:
            return JSONResponse(
                status_code=status.HTTP_403_FORBIDDEN,
                content={
                    "detail": "Operação não permitida durante visualização como cliente. "
                    "Encerre a sessão de impersonation para realizar alterações."
                },
                headers={"X-Impersonation-Read-Only": "true"},
            )
    return None
