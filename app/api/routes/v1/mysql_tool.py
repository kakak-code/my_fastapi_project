from typing import Any, Literal

from fastapi import APIRouter, HTTPException
from loguru import logger
from pydantic import BaseModel

from app.services.mysql import execute_query, is_safe_query

router = APIRouter()


class ToolParameters(BaseModel):
    query: str


class ToolCallRequest(BaseModel):
    function: Literal["mysql_query"]
    parameters: ToolParameters


@router.post("/tool/mysql", tags=["mysql"])
async def handle_mysql_tool(request: ToolCallRequest) -> dict[str, Any]:
    if request.function != "mysql_query":
        raise HTTPException(
            status_code=400, detail="Invalid function name. Only 'mysql_query' is supported."
        )

    query = request.parameters.query

    if not is_safe_query(query):
        raise HTTPException(
            status_code=403,
            detail="Query is not allowed. Only safe SELECT queries are permitted.",
        )

    result = execute_query(query)
    if result.get("status") == "error":
        message = result.get("message", "Query failed")
        logger.error("MySQL query error: {}", message)
        raise HTTPException(status_code=500, detail=message)
    return result

