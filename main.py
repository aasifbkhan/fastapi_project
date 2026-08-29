from fastapi import FastAPI
from api.router import api_router

app = FastAPI(
    title="DevFlow",
    version="1.0.0",
)

app.include_router(api_router, prefix="/api/v1")
