import logging
import sys
from typing import Any, Dict

from loguru import logger

LOGURU_FORMAT = (
    "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
    "<level>{level: <8}</level> | "
    "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
    "<level>{message}</level>"
)


class InterceptHandler(logging.Handler):
    """将标准日志重定向到 loguru。"""

    def emit(self, record: logging.LogRecord) -> None:
        try:
            level = logger.level(record.levelname).name
        except ValueError:
            level = record.levelno
        logger.log(level, record.getMessage())


def setup_logging(level: str = "INFO", serialize: bool = False) -> None:
    # 清理默认处理器
    logging.root.handlers = []
    logging.root.setLevel(logging.getLevelName(level))

    logger.remove()
    logger.add(
        sys.stdout,
        level=level,
        serialize=serialize,
        enqueue=True,
        backtrace=False,
        diagnose=False,
        format=LOGURU_FORMAT,
    )

    # 将 uvicorn/fastapi 默认日志交给 loguru
    for name in ("uvicorn.asgi", "uvicorn.access", "uvicorn.error", "fastapi"):
        logging.getLogger(name).handlers = [InterceptHandler()]
        logging.getLogger(name).propagate = False


def log_configuration(settings: Dict[str, Any]) -> None:
    safe_settings = {k: ("***" if "secret" in k.lower() else v) for k, v in settings.items()}
    logger.debug("Loaded settings: {}", safe_settings)

