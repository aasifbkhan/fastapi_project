"""
Top-level API routers. Versioned APIs are mounted here.
"""
from fastapi import APIRouter

from api.v1.router import v1_router

api_router = APIRouter()

api_router.include_router(v1_router, prefix="/v1")
