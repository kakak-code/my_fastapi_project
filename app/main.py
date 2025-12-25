from contextlib import asynccontextmanager
from typing import Any

from fastapi import Depends, FastAPI, Request
from fastapi.responses import JSONResponse

from app.api import router as api_router
from app.api.dependencies import get_cached_settings
from app.core.config import Settings
from app.core.logging import log_configuration, setup_logging


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_cached_settings()
    setup_logging(level=settings.log_level, serialize=settings.log_json)
    log_configuration(settings.model_dump())
    yield
    # 可在此添加资源释放逻辑（如关闭连接池）


def create_app() -> FastAPI:
    settings = get_cached_settings()
    application = FastAPI(
        title=settings.project_name,
        version=settings.version,
        debug=settings.debug,
        lifespan=lifespan,
    )
    application.include_router(api_router.api_router)
    return application


app = create_app()


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    # 记录未捕获异常，便于排查 500
    from loguru import logger

    logger.exception("Unhandled exception: path={} method={}", request.url.path, request.method)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal Server Error", "hint": "检查日志获取详细错误"},
    )


@app.get("/", summary="根路由")
async def root(settings: Settings = Depends(get_cached_settings)) -> dict[str, Any]:
    return {
        "message": f"Welcome to {settings.project_name}!",
        "usage": "POST /api/v1/tool/mysql 调用 MySQL 查询功能",
        "example_request": {
            "function": "mysql_query",
            "parameters": {"query": "SELECT * FROM your_table LIMIT 10"},
        },
    }

