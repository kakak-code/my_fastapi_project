# FastAPI 项目骨架

一个面向生产环境的 FastAPI 项目基础模板，开箱即用且便于扩展。1111111111222222233333333

## 快速开始

1. 创建虚拟环境并安装依赖：
   ```bash
   uv venv  # 如果未安装 uv，可改用 python -m venv .venv
   source .venv/bin/activate  # Windows: .venv\\Scripts\\activate
   uv pip install -r requirements.txt
   ```
2. 复制环境变量模板并按需调整：
   ```bash
   cp env.example .env
   ```
3.
   ```bash
   uvicorn app.main:app --host 0.0.0.0 --reload
   ```

## MySQL 查询工具

- 启用：在 `.env` 中设置 `MYSQL_ENABLED=true` 并填写 `MYSQL_HOST/PORT/USER/PASSWORD/MYSQL_DB` 等配置。
- 接口：`POST /api/v1/tool/mysql`
- 请求体示例：
  ```json
  {
    "function": "mysql_query",
    "parameters": {
      "query": "SELECT * FROM your_table LIMIT 10"
    }
  }
  ```
- 仅允许安全的 `SELECT` 语句；连接池默认大小 5，可通过 `MYSQL_POOL_SIZE` 调整。

## 目录结构

- `app/main.py`：应用入口，包含生命周期管理与路由注册。
- `app/core/config.py`：集中式配置，基于 Pydantic Settings。
- `app/core/logging.py`：日志配置，兼容控制台与未来文件输出。
- `app/api/routes`：业务路由与健康检查。
- `tests/`：基础测试示例（健康检查）。

## 生产部署提示

- 建议使用进程管理器（如 systemd、supervisord）托管 `uvicorn`/`gunicorn`。
- 将 `.env` 由运维下发，避免提交敏感信息。
- 根据业务需要接入数据库、队列等，并在 `app/core/config.py` 中扩展配置。

