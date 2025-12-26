from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    project_name: str = Field(default="My FastAPI Project")
    environment: Literal["development", "staging", "production"] = Field(default="development")
    debug: bool = Field(default=False)
    api_prefix: str = Field(default="/api")
    version: str = Field(default="0.1.0")

    # 日志
    log_level: str = Field(default="INFO")
    log_json: bool = Field(default=False)

    # MySQL 配置
    mysql_enabled: bool = Field(default=False)
    mysql_host: str = Field(default="127.0.0.1")
    mysql_port: int = Field(default=3306)
    mysql_user: str = Field(default="root")
    mysql_password: str = Field(default="")
    mysql_db: str = Field(default="test")
    mysql_auth_plugin: str = Field(default="mysql_native_password")
    mysql_pool_size: int = Field(default=5)
    mysql_connect_timeout: int = Field(default=10)
    mysql_charset: str = Field(default="utf8mb4")

    # Dify API 配置
    dify_enabled: bool = Field(default=False)
    dify_api_key: str = Field(default="", description="Dify API密钥，请妥善保管")
    dify_base_url: str = Field(default="https://api.dify.ai/v1", description="Dify API基础URL")
    dify_timeout: int = Field(default=60, description="Dify API请求超时时间（秒），AI处理需要更长时间，建议60秒以上")


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()

