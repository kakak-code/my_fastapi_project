import json
import tempfile
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import JSONResponse, StreamingResponse
from loguru import logger
from pydantic import BaseModel, Field

from app.api.dependencies import get_cached_settings
from app.core.config import Settings
from app.services.dify import get_dify_client

router = APIRouter()


class WorkflowRunRequest(BaseModel):
    """工作流执行请求模型"""
    workflow_id: str = Field(..., description="工作流ID")
    inputs: dict[str, Any] = Field(..., description="工作流输入参数")
    file_id: str | None = Field(None, description="已上传的文件ID（可选）")
    response_mode: str = Field(
        default="blocking", description="响应模式：blocking（阻塞）或 streaming（流式）"
    )
    user: str | None = Field(None, description="用户标识（可选，用于隐私保护）")

    class Config:
        json_schema_extra = {
            "example": {
                "workflow_id": "your-workflow-id",
                "inputs": {"param1": "value1", "param2": "value2"},
                "file_id": None,
                "response_mode": "blocking",
                "user": None,
            }
        }


class WorkflowStatusRequest(BaseModel):
    """工作流状态查询请求模型"""
    task_id: str = Field(..., description="任务ID")


class ChatMessageRequest(BaseModel):
    """聊天消息请求模型"""
    query: str = Field(..., description="用户查询文本")
    inputs: dict[str, Any] = Field(default_factory=dict, description="输入参数（可选）")
    response_mode: str = Field(
        default="blocking", description="响应模式：blocking（阻塞）或 streaming（流式）"
    )
    conversation_id: str | None = Field(None, description="会话ID（可选，用于多轮对话）")
    user: str | None = Field(None, description="用户标识（可选，用于隐私保护）")
    files: list[dict[str, Any]] | None = Field(
        None, description="文件列表（可选），支持远程URL或上传文件ID"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "query": "What are the specs of the iPhone 13 Pro Max?",
                "inputs": {},
                "response_mode": "streaming",
                "conversation_id": "",
                "user": "abc-123",
                "files": [
                    {
                        "type": "image",
                        "transfer_method": "remote_url",
                        "url": "https://cloud.dify.ai/logo/logo-site.png",
                    }
                ],
            }
        }


@router.post("/dify/upload", summary="上传文件到Dify", tags=["dify"])
async def upload_file_to_dify(
    file: UploadFile = File(..., description="要上传的文件"),
    user: str | None = None,
    settings: Settings = Depends(get_cached_settings),
) -> dict[str, Any]:
    """
    上传文件到Dify平台（异步实现，不阻塞事件循环）。

    该接口会将上传的文件保存到临时目录，然后调用Dify API上传，上传完成后自动清理临时文件。

    **隐私保护：**
    - API密钥不会在日志中记录
    - 用户信息仅在需要时记录
    - 文件内容不会记录到日志中

    请求示例：
    ```bash
    curl -X POST http://localhost:8000/api/v1/dify/upload \\
      -H "Content-Type: multipart/form-data" \\
      -F "file=@your_file.pdf" \\
      -F "user=user123"
    ```
    """
    if not settings.dify_enabled:
        raise HTTPException(status_code=503, detail="Dify API未启用，请在配置中设置 DIFY_ENABLED=true")

    client = await get_dify_client(settings)
    if not client:
        raise HTTPException(status_code=500, detail="Dify API客户端初始化失败，请检查配置")

    # 创建临时文件保存上传的文件
    temp_file = None
    try:
        # 创建临时文件
        suffix = Path(file.filename).suffix if file.filename else ""
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as temp_file:
            temp_path = Path(temp_file.name)

            # 读取上传的文件内容并写入临时文件
            content = await file.read()
            temp_file.write(content)
            temp_file.flush()

            # 异步调用Dify API上传文件
            result = await client.upload_file(temp_path, user=user)

            if result.get("status") == "error":
                raise HTTPException(status_code=500, detail=result.get("message", "文件上传失败"))

            # 返回结果（不包含敏感信息）
            return {
                "status": "success",
                "file_id": result.get("id"),
                "file_name": result.get("name"),
                "file_size": result.get("size"),
                "file_type": result.get("mime_type"),
            }

    except HTTPException:
        raise
    except Exception as e:
        error_msg = f"文件上传处理异常: {str(e)}"
        logger.error(error_msg)
        raise HTTPException(status_code=500, detail=error_msg)
    finally:
        # 清理临时文件
        if temp_file and temp_path.exists():
            try:
                temp_path.unlink()
                logger.debug(f"已清理临时文件: {temp_path}")
            except Exception as e:
                logger.warning(f"清理临时文件失败: {temp_path}, 错误: {str(e)}")


@router.post("/dify/workflow/run", summary="执行Dify工作流", tags=["dify"])
async def run_dify_workflow(
    request: WorkflowRunRequest,
    settings: Settings = Depends(get_cached_settings),
) -> dict[str, Any]:
    """
    执行Dify工作流（异步实现，不阻塞事件循环）。

    **隐私保护：**
    - API密钥不会在日志中记录
    - 用户输入参数仅在必要时记录
    - 敏感信息不会出现在响应日志中

    请求示例：
    ```json
    {
        "workflow_id": "your-workflow-id",
        "inputs": {
            "param1": "value1",
            "param2": "value2"
        },
        "file_id": "uploaded-file-id",
        "response_mode": "blocking",
        "user": "user123"
    }
    ```
    """
    if not settings.dify_enabled:
        raise HTTPException(status_code=503, detail="Dify API未启用，请在配置中设置 DIFY_ENABLED=true")

    client = await get_dify_client(settings)
    if not client:
        raise HTTPException(status_code=500, detail="Dify API客户端初始化失败，请检查配置")

    try:
        # 验证响应模式
        if request.response_mode not in ["blocking", "streaming"]:
            raise HTTPException(
                status_code=400, detail="response_mode必须是 'blocking' 或 'streaming'"
            )

        # 异步执行工作流
        result = await client.run_workflow(
            workflow_id=request.workflow_id,
            inputs=request.inputs,
            file_id=request.file_id,
            response_mode=request.response_mode,
            user=request.user,
        )

        if result.get("status") == "error":
            raise HTTPException(status_code=500, detail=result.get("message", "工作流执行失败"))

        return {"status": "success", "data": result}

    except HTTPException:
        raise
    except Exception as e:
        error_msg = f"工作流执行处理异常: {str(e)}"
        logger.error(error_msg)
        raise HTTPException(status_code=500, detail=error_msg)


@router.post("/dify/workflow/status", summary="查询工作流执行状态", tags=["dify"])
async def get_workflow_status(
    request: WorkflowStatusRequest,
    settings: Settings = Depends(get_cached_settings),
) -> dict[str, Any]:
    """
    查询工作流执行状态（用于非阻塞模式，异步实现）。

    请求示例：
    ```json
    {
        "task_id": "task-id-from-workflow-run"
    }
    ```
    """
    if not settings.dify_enabled:
        raise HTTPException(status_code=503, detail="Dify API未启用，请在配置中设置 DIFY_ENABLED=true")

    client = await get_dify_client(settings)
    if not client:
        raise HTTPException(status_code=500, detail="Dify API客户端初始化失败，请检查配置")

    try:
        result = await client.get_workflow_status(request.task_id)

        if result.get("status") == "error":
            raise HTTPException(status_code=500, detail=result.get("message", "查询任务状态失败"))

        return {"status": "success", "data": result}

    except HTTPException:
        raise
    except Exception as e:
        error_msg = f"查询任务状态处理异常: {str(e)}"
        logger.error(error_msg)
        raise HTTPException(status_code=500, detail=error_msg)


@router.post(
    "/dify/chat-messages",
    summary="发送聊天消息",
    tags=["dify"],
    response_model=None,
)
async def send_chat_message(
    request: ChatMessageRequest,
    settings: Settings = Depends(get_cached_settings),
):
    """
    发送聊天消息到Dify并获取AI回复（异步实现，不阻塞事件循环）。

    支持两种响应模式：
    - **blocking**（阻塞模式）：等待完整响应后返回
    - **streaming**（流式模式）：使用Server-Sent Events (SSE) 实时返回响应

    **隐私保护：**
    - API密钥不会在日志中记录
    - 用户查询内容仅在必要时记录
    - 敏感信息不会出现在响应日志中

    请求示例（阻塞模式）：
    ```json
    {
        "query": "What are the specs of the iPhone 13 Pro Max?",
        "inputs": {},
        "response_mode": "blocking",
        "conversation_id": "",
        "user": "abc-123",
        "files": [
            {
                "type": "image",
                "transfer_method": "remote_url",
                "url": "https://cloud.dify.ai/logo/logo-site.png"
            }
        ]
    }
    ```

    请求示例（流式模式）：
    ```json
    {
        "query": "What are the specs of the iPhone 13 Pro Max?",
        "response_mode": "streaming",
        "user": "abc-123"
    }
    ```
    """
    if not settings.dify_enabled:
        raise HTTPException(status_code=503, detail="Dify API未启用，请在配置中设置 DIFY_ENABLED=true")

    client = await get_dify_client(settings)
    if not client:
        raise HTTPException(status_code=500, detail="Dify API客户端初始化失败，请检查配置")

    try:
        # 验证响应模式
        if request.response_mode not in ["blocking", "streaming"]:
            raise HTTPException(
                status_code=400, detail="response_mode必须是 'blocking' 或 'streaming'"
            )

        # 异步发送聊天消息
        result = await client.send_chat_message(
            query=request.query,
            inputs=request.inputs,
            response_mode=request.response_mode,
            conversation_id=request.conversation_id,
            user=request.user,
            files=request.files,
        )

        if isinstance(result, dict) and result.get("status") == "error":
            raise HTTPException(status_code=500, detail=result.get("message", "聊天消息发送失败"))

        # 处理流式响应
        if request.response_mode == "streaming" and hasattr(result, "__aiter__"):
            # 返回流式响应（SSE格式）
            async def generate_stream():
                try:
                    buffer = b""
                    async for chunk in result:
                        buffer += chunk
                        # 按行处理SSE格式
                        while b"\n" in buffer:
                            line, buffer = buffer.split(b"\n", 1)
                            line_str = line.decode("utf-8", errors="ignore").strip()
                            if line_str:
                                # 处理SSE格式
                                if line_str.startswith("data: "):
                                    yield line_str.encode("utf-8") + b"\n\n"
                                elif line_str.startswith("event: ") or line_str.startswith("id: "):
                                    yield line_str.encode("utf-8") + b"\n"
                                else:
                                    # 如果不是标准SSE格式，添加"data: "前缀
                                    yield f"data: {line_str}\n\n".encode("utf-8")
                    # 处理剩余的buffer
                    if buffer:
                        yield f"data: {buffer.decode('utf-8', errors='ignore')}\n\n".encode("utf-8")
                except Exception as e:
                    logger.error(f"流式响应处理异常: {str(e)}")
                    error_data = json.dumps({"error": str(e)}, ensure_ascii=False)
                    yield f"data: {error_data}\n\n".encode("utf-8")

            return StreamingResponse(
                generate_stream(),
                media_type="text/event-stream",
                headers={
                    "Cache-Control": "no-cache",
                    "Connection": "keep-alive",
                    "X-Accel-Buffering": "no",
                },
            )
        else:
            # 阻塞模式，返回JSON响应
            # 使用 JSONResponse 确保正确的 UTF-8 编码
            return JSONResponse(
                content={"status": "success", "data": result},
                media_type="application/json; charset=utf-8"
            )

    except HTTPException:
        raise
    except Exception as e:
        error_msg = f"聊天消息处理异常: {str(e)}"
        logger.error(error_msg)
        raise HTTPException(status_code=500, detail=error_msg)
