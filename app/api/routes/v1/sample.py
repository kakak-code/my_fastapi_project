from fastapi import APIRouter, Depends

from app.api.dependencies import get_cached_settings
from app.core.config import Settings

router = APIRouter()


@router.get("/info", summary="示例信息")
async def get_info(settings: Settings = Depends(get_cached_settings)) -> dict[str, str]:
    return {
        "project": settings.project_name,
        "environment": settings.environment,
        "version": settings.version,
    }

