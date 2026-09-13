"""
API v1 feature routers (auth, users, etc.).
"""
from fastapi import APIRouter

from api.v1.auth.router import router as auth_router

v1_router = APIRouter()

v1_router.include_router(auth_router)
