"""
Devflow intitalization module
"""
from fastapi import FastAPI
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from api.router import api_router
from core.rate_limit import limiter
from middleware.auth import AuthJWTMiddleware

app = FastAPI(
    title="DevFlow",
    version="1.0.0",
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)
app.add_middleware(AuthJWTMiddleware)

app.include_router(api_router, prefix="/api")
