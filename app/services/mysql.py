from functools import lru_cache
from typing import Any

import mysql.connector
from loguru import logger
from mysql.connector import Error, pooling

from app.api.dependencies import get_cached_settings
from app.core.config import Settings


def is_safe_query(query: str) -> bool:
    """验证查询是否为安全的 SELECT 语句，避免危险操作。"""
    if not query or not isinstance(query, str):
        return False

    cleaned_query = query.strip().rstrip(";").strip().upper()

    if not cleaned_query.startswith("SELECT"):
        return False

    dangerous_keywords = [
        "DELETE",
        "UPDATE",
        "INSERT",
        "DROP",
        "ALTER",
        "TRUNCATE",
        "CREATE",
        "RENAME",
        "REPLACE",
        "GRANT",
        "REVOKE",
    ]
    for keyword in dangerous_keywords:
        if f" {keyword} " in f" {cleaned_query} ":
            return False

    return True


def _build_db_config(settings: Settings) -> dict[str, Any]:
    return {
        "host": settings.mysql_host,
        "port": settings.mysql_port,
        "user": settings.mysql_user,
        "password": settings.mysql_password,
        "database": settings.mysql_db,
        "auth_plugin": settings.mysql_auth_plugin,
        "connect_timeout": settings.mysql_connect_timeout,
        "charset": settings.mysql_charset,
    }


@lru_cache(maxsize=1)
def get_pool() -> pooling.MySQLConnectionPool | None:
    """创建或获取 MySQL 连接池，失败时返回 None。"""
    settings = get_cached_settings()
    if not settings.mysql_enabled:
        logger.warning("MySQL 功能未启用，跳过连接池初始化")
        return None

    try:
        pool = pooling.MySQLConnectionPool(
            pool_name="mysql_pool",
            pool_size=settings.mysql_pool_size,
            pool_reset_session=True,
            **_build_db_config(settings),
        )
        logger.info("MySQL 连接池初始化成功 pool_size={}", settings.mysql_pool_size)
        return pool
    except Error as exc:
        logger.error("MySQL 连接池创建失败: {}", exc)
        return None


def execute_query(query: str, settings: Settings | None = None) -> dict[str, Any]:
    """执行只读查询并返回结果字典。"""
    settings = settings or get_cached_settings()
    pool = get_pool()
    if not pool:
        return {"status": "error", "message": "MySQL 连接池未初始化或功能未启用"}

    connection = None
    cursor = None
    try:
        connection = pool.get_connection()
        cursor = connection.cursor(dictionary=True)
        cursor.execute(query)
        rows = cursor.fetchall()
        return {"status": "success", "data": rows, "row_count": len(rows)}
    except Error as exc:
        logger.error("MySQL 查询失败: {}", exc)
        return {"status": "error", "message": f"数据库查询失败: {exc}"}
    finally:
        if cursor:
            cursor.close()
        if connection and connection.is_connected():
            connection.close()

