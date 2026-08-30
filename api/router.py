"""
All the api routes are included here. e.g. auth, user etc.
"""
from fastapi import APIRouter
from api.auth.router import router as auth_router

api_router = APIRouter()

api_router.include_router(auth_router)
