from functools import lru_cache

from app.core.config import Settings, get_settings


@lru_cache(maxsize=1)
def get_cached_settings() -> Settings:
    # 作为 FastAPI Depends 使用，避免重复实例化
    return get_settings()

