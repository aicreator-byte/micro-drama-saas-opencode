from fastapi import APIRouter

from app.api.v1 import api_router

api_router = APIRouter()

api_router.include_router(api_router, prefix="/api/v1")