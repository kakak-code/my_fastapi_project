from fastapi import APIRouter

from app.api.routes.v1 import extractor, mysql_tool, sample

router = APIRouter()

router.include_router(sample.router, tags=["sample"])
router.include_router(mysql_tool.router, tags=["mysql"])
router.include_router(extractor.router, tags=["extractor"])

