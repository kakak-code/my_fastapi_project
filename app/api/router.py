from fastapi import APIRouter

from app.api.routes import health, v1
from app.core.config import get_settings

settings = get_settings()

api_router = APIRouter(prefix=settings.api_prefix)

api_router.include_router(health.router, tags=["health"])
api_router.include_router(v1.router, prefix="/v1")

