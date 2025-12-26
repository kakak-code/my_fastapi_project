# Dify API 使用指南

本指南介绍如何在项目中使用 Dify API 功能，包括文件上传、工作流执行和聊天消息。

## 目录

1. [环境配置](#环境配置)
2. [API端点](#api端点)
3. [使用示例](#使用示例)
   - [文件上传](#1-文件上传)
   - [执行工作流](#2-执行工作流)
   - [发送聊天消息](#3-发送聊天消息)
   - [查询工作流状态](#4-查询工作流状态)
4. [Python客户端示例](#python客户端示例)
5. [常见问题](#常见问题)

## 环境配置

### 1. 安装依赖

确保已安装所有依赖：

```bash
pip install -r requirements.txt
```

### 2. 配置环境变量

在 `.env` 文件中配置 Dify API 相关参数：

```env
# Dify API 配置
DIFY_ENABLED=true
DIFY_API_KEY="your-dify-api-key-here"
DIFY_BASE_URL="https://api.dify.ai/v1"
DIFY_TIMEOUT=30
```

**重要提示：**
- `DIFY_API_KEY`: 从 Dify 平台获取的 API 密钥
- `DIFY_BASE_URL`: Dify API 基础URL，默认为 `https://api.dify.ai/v1`
- `DIFY_TIMEOUT`: 请求超时时间（秒），默认30秒

### 3. 启动服务

```bash
uvicorn app.main:app --host 0.0.0.0 --reload
```

服务启动后，API 文档可在以下地址访问：
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## API端点

### 基础路径

所有 Dify API 端点都在 `/api/v1/dify/` 路径下：

- `POST /api/v1/dify/upload` - 上传文件
- `POST /api/v1/dify/workflow/run` - 执行工作流
- `POST /api/v1/dify/workflow/status` - 查询工作流状态
- `POST /api/v1/dify/chat-messages` - 发送聊天消息

## 使用示例

### 1. 文件上传

上传文件到 Dify 平台，获取文件ID用于后续操作。

#### cURL 示例

```bash
curl -X POST 'http://localhost:8000/api/v1/dify/upload' \
  -H 'Content-Type: multipart/form-data' \
  -F 'file=@/path/to/your/file.pdf' \
  -F 'user=user123'
```

#### 响应示例

```json
{
  "status": "success",
  "file_id": "file-abc123xyz",
  "file_name": "document.pdf",
  "file_size": 102400,
  "file_type": "application/pdf"
}
```

#### Python 示例

```python
import requests

url = "http://localhost:8000/api/v1/dify/upload"
files = {"file": open("document.pdf", "rb")}
data = {"user": "user123"}

response = requests.post(url, files=files, data=data)
result = response.json()
print(f"文件ID: {result['file_id']}")
```

### 2. 执行工作流

执行 Dify 工作流，支持阻塞和流式两种响应模式。

#### cURL 示例（阻塞模式）

```bash
curl -X POST 'http://localhost:8000/api/v1/dify/workflow/run' \
  -H 'Content-Type: application/json' \
  -d '{
    "workflow_id": "your-workflow-id",
    "inputs": {
      "param1": "value1",
      "param2": "value2"
    },
    "file_id": "file-abc123xyz",
    "response_mode": "blocking",
    "user": "user123"
  }'
```

#### 响应示例

```json
{
  "status": "success",
  "data": {
    "id": "task-123",
    "status": "success",
    "outputs": {
      "result": "处理结果..."
    }
  }
}
```

#### Python 示例

```python
import requests

url = "http://localhost:8000/api/v1/dify/workflow/run"
payload = {
    "workflow_id": "your-workflow-id",
    "inputs": {
        "param1": "value1",
        "param2": "value2"
    },
    "file_id": "file-abc123xyz",
    "response_mode": "blocking",
    "user": "user123"
}

response = requests.post(url, json=payload)
result = response.json()
print(result)
```

### 3. 发送聊天消息

发送聊天消息到 Dify，支持阻塞和流式两种响应模式。

#### cURL 示例（阻塞模式）

```bash
curl -Method POST `
  -Uri 'http://localhost:8000/api/v1/dify/chat-messages' `
  -ContentType 'application/json' `
  -TimeoutSec 30 `
  -Body '{
    "user": "abc-123",
    "conversation_id": "",
    "response_mode": "blocking",
    "inputs": {},
    "query": "查询价格大于5000的商品?",
    "files": [
      {
        "url": "https://cloud.dify.ai/logo/logo-site.png",
        "transfer_method": "remote_url",
        "type": "image"
      }
    ]
  }'
```

# 2. 定义请求体并转换为 JSON
$body = @{
    user = "abc-123"
    conversation_id = ""
    response_mode = "blocking"
    inputs = @{}
    query = "查询价格大于5000的商品"
} | ConvertTo-Json -Depth 10

# 3. 发送请求并获取响应（中文直接正常显示）
$response = Invoke-RestMethod -Method Post `
    -Uri 'http://localhost:8000/api/v1/dify/chat-messages' `
    -ContentType 'application/json; charset=utf-8' `
    -Body $body `
    -TimeoutSec 180

# 4. 格式化输出完整响应结果
$response | ConvertTo-Json -Depth 10


#### cURL 示例（流式模式）

```bash
curl -Method POST `
  -Uri 'http://localhost:8000/api/v1/dify/chat-messages' `
  -ContentType 'application/json' `
  -Body '{
    "query": "查询价格大于5000的商品?",
    "inputs": {},
    "response_mode": "streaming",
    "conversation_id": "",
    "user": "abc-123"
  }'
```
流式响应会以 Server-Sent Events (SSE) 格式返回：

```
data: {"event": "message", "answer": "The iPhone 13 Pro Max..."}

data: {"event": "message", "answer": " features include..."}

data: {"event": "message_end"}
```

#### Python 示例（阻塞模式）

```python
import requests

url = "http://localhost:8000/api/v1/dify/chat-messages"
payload = {
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

response = requests.post(url, json=payload)
result = response.json()
print(result)
```

#### Python 示例（流式模式）

```python
import requests
import json

url = "http://localhost:8000/api/v1/dify/chat-messages"
payload = {
    "query": "What are the specs of the iPhone 13 Pro Max?",
    "inputs": {},
    "response_mode": "streaming",
    "user": "abc-123"
}

response = requests.post(url, json=payload, stream=True)

for line in response.iter_lines():
    if line:
        decoded = line.decode('utf-8')
        if decoded.startswith('data: '):
            data = decoded[6:]  # 移除 "data: " 前缀
            try:
                event_data = json.loads(data)
                print(event_data)
            except json.JSONDecodeError:
                print(data)
```

### 4. 查询工作流状态

查询非阻塞模式下执行的工作流状态。

#### cURL 示例

```bash
curl -X POST 'http://localhost:8000/api/v1/dify/workflow/status' \
  -H 'Content-Type: application/json' \
  -d '{
    "task_id": "task-id-from-workflow-run"
  }'
```

#### Python 示例

```python
import requests

url = "http://localhost:8000/api/v1/dify/workflow/status"
payload = {
    "task_id": "task-id-from-workflow-run"
}

response = requests.post(url, json=payload)
result = response.json()
print(result)
```

## Python客户端示例

### 完整使用流程示例

```python
import requests
import json

BASE_URL = "http://localhost:8000/api/v1/dify"

# 1. 上传文件
print("1. 上传文件...")
with open("document.pdf", "rb") as f:
    files = {"file": f}
    data = {"user": "user123"}
    response = requests.post(f"{BASE_URL}/upload", files=files, data=data)
    upload_result = response.json()
    file_id = upload_result.get("file_id")
    print(f"文件上传成功，文件ID: {file_id}")

# 2. 执行工作流（使用上传的文件）
print("\n2. 执行工作流...")
workflow_payload = {
    "workflow_id": "your-workflow-id",
    "inputs": {
        "document": "请分析这个文档"
    },
    "file_id": file_id,
    "response_mode": "blocking",
    "user": "user123"
}
response = requests.post(f"{BASE_URL}/workflow/run", json=workflow_payload)
workflow_result = response.json()
print(f"工作流执行结果: {workflow_result}")

# 3. 发送聊天消息
print("\n3. 发送聊天消息...")
chat_payload = {
    "query": "请总结一下刚才上传的文档",
    "inputs": {},
    "response_mode": "blocking",
    "conversation_id": "",
    "user": "user123"
}
response = requests.post(f"{BASE_URL}/chat-messages", json=chat_payload)
chat_result = response.json()
print(f"聊天回复: {chat_result}")
```

### 流式聊天示例

```python
import requests
import json
import sys

def stream_chat(query: str, user: str = "user123"):
    """流式发送聊天消息"""
    url = "http://localhost:8000/api/v1/dify/chat-messages"
    payload = {
        "query": query,
        "inputs": {},
        "response_mode": "streaming",
        "user": user
    }
    
    response = requests.post(url, json=payload, stream=True)
    
    for line in response.iter_lines():
        if line:
            decoded = line.decode('utf-8')
            if decoded.startswith('data: '):
                data_str = decoded[6:]
                try:
                    event_data = json.loads(data_str)
                    # 处理不同类型的事件
                    if event_data.get('event') == 'message':
                        answer = event_data.get('answer', '')
                        sys.stdout.write(answer)
                        sys.stdout.flush()
                    elif event_data.get('event') == 'message_end':
                        print("\n[消息结束]")
                        break
                except json.JSONDecodeError:
                    pass

# 使用示例
stream_chat("请介绍一下人工智能的发展历史")
```

## 常见问题

### 1. API密钥未配置

**错误信息：** `Dify API未启用，请在配置中设置 DIFY_ENABLED=true`

**解决方法：**
- 检查 `.env` 文件中是否设置了 `DIFY_ENABLED=true`
- 确保 `DIFY_API_KEY` 已正确配置

### 2. 文件上传失败

**可能原因：**
- 文件路径不正确
- 文件大小超过限制
- 网络连接问题

**解决方法：**
- 检查文件路径是否正确
- 检查文件大小是否符合 Dify 平台限制
- 检查网络连接

### 3. 流式响应无法接收

**可能原因：**
- 客户端不支持 SSE 格式
- 网络连接中断

**解决方法：**
- 使用支持 SSE 的客户端（如 `requests` 库的 `stream=True` 参数）
- 检查网络连接稳定性

### 4. 工作流执行超时

**解决方法：**
- 增加 `DIFY_TIMEOUT` 配置值
- 检查工作流复杂度，考虑优化工作流

## 隐私保护

本项目已实现以下隐私保护措施：

1. **API密钥安全**：API密钥存储在环境变量中，不会出现在日志或响应中
2. **用户信息保护**：支持用户标识参数，便于追踪和权限控制
3. **日志安全**：日志中不记录敏感信息（API密钥、完整文件内容等）
4. **临时文件清理**：上传后自动清理临时文件

## 更多信息

- Dify 官方文档：https://docs.dify.ai
- FastAPI 文档：https://fastapi.tiangolo.com
- 项目 API 文档：http://localhost:8000/docs

