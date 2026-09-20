"""
JWT authentication middleware for protected routes.
"""
from uuid import UUID

import jwt
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from core.database import async_session_factory
from core.security import TOKEN_TYPE_ACCESS, decode_token
from repositories.user_repository import UserRepository

# Paths that never require a Bearer access token.
PUBLIC_PATHS = frozenset(
    {
        "/api/v1/auth/signup",
        "/api/v1/auth/verify-email",
        "/api/v1/auth/login",
        "/api/v1/auth/refresh",
        "/api/v1/auth/forget-password",
        "/api/v1/auth/reset-password",
        "/docs",
        "/openapi.json",
        "/redoc",
    }
)

# Paths that require a valid Bearer access token.
PROTECTED_PATHS = frozenset(
    {
        "/api/v1/auth/change-password",
    }
)


def _unauthorized(detail: str = "Not authenticated") -> JSONResponse:
    return JSONResponse(status_code=401, content={"detail": detail})


class AuthJWTMiddleware(BaseHTTPMiddleware):
    """
    Validate Bearer access JWTs for protected paths and attach user to request.state.
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        path = request.url.path

        if path in PUBLIC_PATHS or path not in PROTECTED_PATHS:
            return await call_next(request)

        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            return _unauthorized()

        raw_token = auth_header.removeprefix("Bearer ").strip()
        if not raw_token:
            return _unauthorized()

        try:
            payload = decode_token(raw_token, TOKEN_TYPE_ACCESS)
            user_id = UUID(payload["sub"])
        except (jwt.PyJWTError, ValueError, TypeError, KeyError):
            return _unauthorized("Invalid or expired token")

        async with async_session_factory() as session:
            user = await UserRepository().get_by_id(user_id, session)
            if user is None or not user.is_active:
                return _unauthorized("Invalid or expired token")
            # Ensure attributes are loaded, then detach for use outside this session.
            _ = (user.id, user.email, user.password, user.is_active)
            session.expunge(user)
            request.state.user = user

        return await call_next(request)
