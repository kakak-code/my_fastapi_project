import asyncio
from pathlib import Path
from typing import Any, AsyncIterator

import aiohttp
from loguru import logger

from app.core.config import Settings


class DifyAPIClient:
    """Dify API客户端，提供文件上传和工作流执行功能（异步实现）"""

    def __init__(self, api_key: str, base_url: str, timeout: int):
        """
        初始化Dify API客户端

        Args:
            api_key: Dify API密钥
            base_url: Dify API基础URL
            timeout: 请求超时时间（秒），严格超时控制
        """
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        # 设置更宽松的超时：总超时、连接超时、读取超时
        # 对于AI API，通常需要更长的响应时间
        self.timeout = aiohttp.ClientTimeout(
            total=timeout * 2,  # 总超时时间翻倍，给AI处理留出时间
            connect=15,  # 连接超时15秒
            sock_read=timeout * 2,  # 读取超时翻倍
            sock_connect=15  # Socket连接超时
        )
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        self._session: aiohttp.ClientSession | None = None

    async def _get_session(self) -> aiohttp.ClientSession:
        """获取或创建 aiohttp 会话"""
        if self._session is None or self._session.closed:
            connector = aiohttp.TCPConnector(limit=100, limit_per_host=30)
            self._session = aiohttp.ClientSession(
                headers=self.headers,
                timeout=self.timeout,
                connector=connector,
            )
        return self._session

    async def close(self):
        """关闭客户端会话"""
        if self._session and not self._session.closed:
            await self._session.close()

    async def upload_file(
        self, file_path: str | Path, user: str | None = None
    ) -> dict[str, Any]:
        """
        异步上传文件到Dify并返回文件信息

        Args:
            file_path: 文件路径
            user: 用户标识（可选，用于隐私保护）

        Returns:
            包含文件ID和文件信息的字典，格式：{"id": "file_id", "name": "file_name", ...}
            如果上传失败，返回 {"status": "error", "message": "错误信息"}
        """
        file_path = Path(file_path)
        if not file_path.exists():
            error_msg = f"文件不存在: {file_path}"
            logger.error(error_msg)
            return {"status": "error", "message": error_msg}

        upload_url = f"{self.base_url}/files/upload"

        try:
            session = await self._get_session()
            
            # 读取文件内容
            with open(file_path, "rb") as file:
                file_content = file.read()

            # 准备表单数据
            data = aiohttp.FormData()
            data.add_field("file", file_content, filename=file_path.name, content_type="application/octet-stream")
            if user:
                data.add_field("user", user)

            # 使用严格超时控制
            headers = {"Authorization": f"Bearer {self.api_key}"}
            
            async with session.post(
                upload_url, 
                data=data, 
                headers=headers,
                timeout=self.timeout
            ) as response:
                if response.status == 200:
                    result = await response.json()
                    logger.info(
                        f"文件上传成功: {file_path.name}, 文件ID: {result.get('id', 'N/A')[:8]}..."
                    )
                    return result
                else:
                    error_text = await response.text()
                    error_msg = f"文件上传失败，状态码: {response.status}, 响应: {error_text[:200]}"
                    logger.error(error_msg)
                    return {"status": "error", "message": error_msg}

        except asyncio.TimeoutError:
            error_msg = f"文件上传超时: {file_path} (超时时间: {self.timeout.total}秒)"
            logger.error(error_msg)
            return {"status": "error", "message": error_msg}
        except aiohttp.ClientError as e:
            error_msg = f"文件上传请求异常: {str(e)}"
            logger.error(error_msg)
            return {"status": "error", "message": error_msg}
        except Exception as e:
            error_msg = f"文件上传未知错误: {str(e)}"
            logger.error(error_msg)
            return {"status": "error", "message": error_msg}

    async def run_workflow(
        self,
        workflow_id: str,
        inputs: dict[str, Any],
        file_id: str | None = None,
        response_mode: str = "blocking",
        user: str | None = None,
    ) -> dict[str, Any]:
        """
        异步执行Dify工作流

        Args:
            workflow_id: 工作流ID
            inputs: 工作流输入参数
            file_id: 上传的文件ID（可选）
            response_mode: 响应模式，可选值: "blocking"（阻塞）或 "streaming"（流式），默认"blocking"
            user: 用户标识（可选，用于隐私保护）

        Returns:
            工作流执行结果字典
            如果执行失败，返回 {"status": "error", "message": "错误信息"}
        """
        workflow_url = f"{self.base_url}/workflows/run"

        # 构建请求数据
        data: dict[str, Any] = {
            "inputs": inputs,
            "response_mode": response_mode,
        }

        # 如果提供了文件ID，添加到输入中
        if file_id:
            data["inputs"]["file"] = {
                "transfer_method": "local_file",
                "upload_file_id": file_id,
                "type": "document",
            }

        # 添加用户参数（如果提供）
        if user:
            data["user"] = user

        try:
            logger.info(
                f"执行工作流: {workflow_id}, 响应模式: {response_mode}, 包含文件: {file_id is not None}"
            )

            session = await self._get_session()
            
            async with session.post(
                workflow_url, 
                json=data, 
                timeout=self.timeout
            ) as response:
                if response.status == 200:
                    result = await response.json()
                    logger.info(f"工作流执行成功: {workflow_id}")
                    return result
                else:
                    error_text = await response.text()
                    error_msg = (
                        f"工作流执行失败，状态码: {response.status}, "
                        f"响应: {error_text[:200]}"
                    )
                    logger.error(error_msg)
                    return {"status": "error", "message": error_msg}

        except asyncio.TimeoutError:
            error_msg = f"工作流执行超时: {workflow_id} (超时时间: {self.timeout.total}秒)"
            logger.error(error_msg)
            return {"status": "error", "message": error_msg}
        except aiohttp.ClientError as e:
            error_msg = f"工作流执行请求异常: {str(e)}"
            logger.error(error_msg)
            return {"status": "error", "message": error_msg}
        except Exception as e:
            error_msg = f"工作流执行未知错误: {str(e)}"
            logger.error(error_msg)
            return {"status": "error", "message": error_msg}

    async def get_workflow_status(self, task_id: str) -> dict[str, Any]:
        """
        异步获取工作流执行状态（用于非阻塞模式）

        Args:
            task_id: 任务ID

        Returns:
            任务状态信息字典
        """
        status_url = f"{self.base_url}/tasks/{task_id}"

        try:
            session = await self._get_session()
            
            async with session.get(
                status_url, 
                timeout=self.timeout
            ) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    error_text = await response.text()
                    error_msg = (
                        f"获取任务状态失败，状态码: {response.status}, "
                        f"响应: {error_text[:200]}"
                    )
                    logger.error(error_msg)
                    return {"status": "error", "message": error_msg}

        except asyncio.TimeoutError:
            error_msg = f"获取任务状态超时: {task_id} (超时时间: {self.timeout.total}秒)"
            logger.error(error_msg)
            return {"status": "error", "message": error_msg}
        except aiohttp.ClientError as e:
            error_msg = f"获取任务状态请求异常: {str(e)}"
            logger.error(error_msg)
            return {"status": "error", "message": error_msg}

    async def send_chat_message(
        self,
        query: str,
        inputs: dict[str, Any] | None = None,
        response_mode: str = "blocking",
        conversation_id: str | None = None,
        user: str | None = None,
        files: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any] | AsyncIterator[bytes]:
        """
        异步发送聊天消息到Dify

        Args:
            query: 用户查询文本
            inputs: 输入参数（可选）
            response_mode: 响应模式，"blocking"（阻塞）或 "streaming"（流式），默认"blocking"
            conversation_id: 会话ID（可选，用于多轮对话）
            user: 用户标识（可选，用于隐私保护）
            files: 文件列表（可选），格式：[{"type": "image", "transfer_method": "remote_url", "url": "..."}]

        Returns:
            如果 response_mode="blocking"，返回结果字典
            如果 response_mode="streaming"，返回异步迭代器（用于流式读取）
            如果失败，返回 {"status": "error", "message": "错误信息"}
        """
        chat_url = f"{self.base_url}/chat-messages"

        # 构建请求数据
        data: dict[str, Any] = {
            "query": query,
            "response_mode": response_mode,
        }

        if inputs:
            data["inputs"] = inputs
        else:
            data["inputs"] = {}

        if conversation_id:
            data["conversation_id"] = conversation_id

        if user:
            data["user"] = user

        if files:
            data["files"] = files

        try:
            logger.info(
                f"发送聊天消息，响应模式: {response_mode}, "
                f"会话ID: {conversation_id[:8] if conversation_id else 'None'}..., "
                f"包含文件: {len(files) if files else 0}"
            )

            session = await self._get_session()

            if response_mode == "streaming":
                # 流式响应，返回异步迭代器
                # 注意：流式响应需要保持连接打开，使用单独的请求
                response = await session.post(
                    chat_url,
                    json=data,
                    timeout=self.timeout,
                )
                
                if response.status == 200:
                    # 返回异步迭代器，逐块读取流式数据
                    async def stream_generator():
                        try:
                            async for chunk in response.content.iter_chunked(8192):
                                yield chunk
                        except Exception as e:
                            logger.error(f"流式读取异常: {str(e)}")
                        finally:
                            if not response.closed:
                                response.close()
                    
                    return stream_generator()
                else:
                    error_text = await response.text()
                    if not response.closed:
                        response.close()
                    error_msg = (
                        f"聊天消息发送失败，状态码: {response.status}, "
                        f"响应: {error_text[:200]}"
                    )
                    logger.error(error_msg)
                    return {"status": "error", "message": error_msg}
            else:
                # 阻塞响应
                async with session.post(
                    chat_url, 
                    json=data, 
                    timeout=self.timeout
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        logger.info("聊天消息发送成功")
                        return result
                    else:
                        error_text = await response.text()
                        error_msg = (
                            f"聊天消息发送失败，状态码: {response.status}, "
                            f"响应: {error_text[:200]}"
                        )
                        logger.error(error_msg)
                        return {"status": "error", "message": error_msg}

        except asyncio.TimeoutError:
            error_msg = f"聊天消息发送超时 (超时时间: {self.timeout.total}秒)"
            logger.error(error_msg)
            return {"status": "error", "message": error_msg}
        except aiohttp.ClientError as e:
            error_msg = f"聊天消息发送请求异常: {str(e)}"
            logger.error(error_msg)
            return {"status": "error", "message": error_msg}
        except Exception as e:
            error_msg = f"聊天消息发送未知错误: {str(e)}"
            logger.error(error_msg)
            return {"status": "error", "message": error_msg}


async def get_dify_client(settings: Settings | None = None) -> DifyAPIClient | None:
    """
    获取Dify API客户端实例（异步）

    Args:
        settings: 应用配置，如果为None则从环境变量读取

    Returns:
        DifyAPIClient实例，如果未启用或配置无效则返回None
    """
    if settings is None:
        from app.core.config import get_settings

        settings = get_settings()

    if not settings.dify_enabled:
        logger.warning("Dify API未启用，请在配置中设置 DIFY_ENABLED=true")
        return None

    if not settings.dify_api_key:
        logger.error("Dify API密钥未配置，请设置 DIFY_API_KEY")
        return None

    return DifyAPIClient(
        api_key=settings.dify_api_key,
        base_url=settings.dify_base_url,
        timeout=settings.dify_timeout,
    )
