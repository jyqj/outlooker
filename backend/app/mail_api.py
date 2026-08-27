#!/usr/bin/env python3
"""
Microsoft邮件管理API
基于FastAPI的现代化异步实现
重构版本：使用模块化架构 + React前端
"""

import asyncio
import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path

import sentry_sdk
from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from sentry_sdk.integrations.fastapi import FastApiIntegration
from sentry_sdk.integrations.starlette import StarletteIntegration

from .core.exceptions import AppException
from .core.middleware import MetricsMiddleware
from .core.startup import log_startup_info, validate_environment
from .core.static_assets import StaticAssetCacheMiddleware, resolve_static_asset
from .db import db_manager
from .models import ApiResponse
from .routers import (
    accounts,
    auth,
    batch,
    dashboard,
    emails,
    outlook_accounts,
    outlook_channels,
    outlook_protocol,
    outlook_resources,
    outlook_tasks,
    public_accounts,
    system,
    tags,
)
from .services import admin_auth_service, email_manager, load_accounts_config
from .services.token_refresh_service import (
    start_background_refresh,
    stop_background_refresh,
)
from .settings import get_settings
from .version import __version__

logger = logging.getLogger(__name__)
settings = get_settings()

# Initialize Sentry for error tracking (only if DSN is configured)
sentry_dsn = os.getenv("SENTRY_DSN")
if sentry_dsn:
    sentry_sdk.init(
        dsn=sentry_dsn,
        environment=settings.app_env,
        integrations=[
            StarletteIntegration(),
            FastApiIntegration(),
        ],
        traces_sample_rate=0.1 if settings.is_production else 1.0,
        profiles_sample_rate=0.1 if settings.is_production else 1.0,
    )
    logger.info("Sentry error tracking initialized")

ALLOWED_ORIGINS = settings.allowed_origins
PROJECT_ROOT = Path(__file__).resolve().parents[2]
STATIC_DIR = (PROJECT_ROOT / settings.static_dir).resolve()


async def _shutdown_application_resources() -> None:
    """Close independent resources even if another cleanup step fails."""
    try:
        await stop_background_refresh()
    except Exception:
        logger.exception("停止后台 Token 刷新任务失败")

    try:
        await email_manager.cleanup_all()
    except Exception:
        logger.exception("清理 IMAP 客户端失败")

    try:
        # ThreadPoolExecutor.shutdown(wait=True) is blocking by design.
        await asyncio.to_thread(db_manager.close)
    except Exception:
        logger.exception("关闭数据库线程池失败")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用程序生命周期管理"""
    logger.info("启动邮件管理系统...")

    log_startup_info()

    warnings = validate_environment()
    for warning in warnings:
        logger.warning("[配置警告] %s", warning)

    if settings.is_production:
        insecure = []
        if (settings.jwt_secret_key or "").endswith("change-me"):
            insecure.append("JWT_SECRET_KEY")
        if (settings.data_encryption_key or "").endswith("change-me"):
            insecure.append("DATA_ENCRYPTION_KEY")
        if settings.client_id == "dbc8e03a-b00c-46bd-ae65-b683e7707cb0":
            insecure.append("CLIENT_ID")

        if insecure:
            items = ", ".join(insecure)
            message = f"[安全警告] 生产环境禁止使用默认配置: {items}"
            logger.error(message)
            raise RuntimeError(message)

    logger.info("初始化数据库...")
    try:
        await admin_auth_service.bootstrap_default_admin()
    except Exception as exc:
        logger.error("初始化默认管理员失败: %s", exc)

    start_background_refresh()

    try:
        yield
    finally:
        logger.info("正在关闭邮件管理系统...")
        await _shutdown_application_resources()
        logger.info("邮件管理系统已关闭")


_API_DESCRIPTION = """
## Outlooker API

Outlook 邮箱验证码管理平台 REST API。

### 认证方式

- **管理员接口** (`/api/accounts`, `/api/system`, `/api/tags` 等)：Bearer JWT Token
  - 通过 `POST /api/admin/login` 获取 token
- **公共接口** (`/api/messages`, `/api/test-email`)：`X-Public-Token` Header

### 主要功能模块

| 模块 | 前缀 | 说明 |
|------|------|------|
| 认证 | `/api/admin` | 登录、刷新、登出 |
| 账户 | `/api/accounts` | CRUD、批量操作、标签、健康检测 |
| 邮件 | `/api/messages` | 获取邮件、验证码提取 |
| 标签 | `/api/tags` | 标签管理 |
| 系统 | `/api/system` | 配置、指标、缓存、提取规则 |
| 审计 | `/api/audit` | 审计日志 |
| 仪表盘 | `/api/dashboard` | 聚合概要 |
"""

app = FastAPI(
    title="Outlooker API",
    description=_API_DESCRIPTION,
    version=__version__,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(MetricsMiddleware)
app.add_middleware(StaticAssetCacheMiddleware)

# Mount API routers
app.include_router(auth.router)
app.include_router(tags.router)
app.include_router(accounts.router)
app.include_router(batch.router)
app.include_router(dashboard.router)
app.include_router(emails.router)
app.include_router(system.router)
app.include_router(public_accounts.router)
app.include_router(outlook_accounts.router)
app.include_router(outlook_channels.router)
app.include_router(outlook_protocol.router)
app.include_router(outlook_resources.router)
app.include_router(outlook_tasks.router)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    logger.error("Pydantic验证错误: %s", exc)
    return JSONResponse(
        status_code=422,
        content=ApiResponse(
            success=False,
            message="数据验证失败",
            error_code="VALIDATION_ERROR",
            data={"details": exc.errors()},
        ).model_dump(),
    )


@app.exception_handler(AppException)
async def app_exception_handler(request: Request, exc: AppException):
    """统一处理应用自定义异常"""
    logger.warning("应用异常: %s - %s", exc.error_code, exc.message)
    payload = ApiResponse(
        success=False,
        message=exc.message,
        error_code=exc.error_code,
        data=exc.details if exc.details else None,
    ).model_dump()
    payload["detail"] = exc.message
    return JSONResponse(status_code=exc.status_code, content=payload)


# Mount Vite's hashed output separately so URLs stay stable and cacheable.
static_assets_path = STATIC_DIR / "assets"
if static_assets_path.exists():
    app.mount("/assets", StaticFiles(directory=static_assets_path), name="assets")
else:
    logger.warning("%s 目录不存在，前端可能未构建", static_assets_path)

# Keep the legacy /static prefix for compatibility with existing deployments.
if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
else:
    logger.warning("静态目录 %s 不存在", STATIC_DIR)


@app.get("/{full_path:path}", include_in_schema=False)
async def serve_spa(full_path: str):
    """Serve root public assets first, then fall back to the SPA document."""
    if full_path.startswith("api/") or full_path.startswith("docs") or full_path.startswith("redoc"):
        raise HTTPException(status_code=404, detail="Not Found")

    # Vite copies files from frontend/public to the output root. Serving a real
    # file here prevents /favicon.svg and similar assets from receiving index.html.
    static_file = resolve_static_asset(STATIC_DIR, full_path)
    if static_file is not None:
        return FileResponse(static_file)

    index_path = STATIC_DIR / "index.html"
    if index_path.exists():
        return FileResponse(index_path)

    placeholder = """
<!doctype html>
<html lang="zh-CN">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>Outlooker</title>
  </head>
  <body>
    <main>
      <h1>Outlooker</h1>
      <p>Frontend not built. Please run 'npm run build' in frontend directory.</p>
    </main>
  </body>
</html>
""".strip()
    return HTMLResponse(placeholder)


async def main():
    """命令行模式入口"""
    try:
        loaded_accounts = await load_accounts_config()
        if not loaded_accounts:
            print("没有找到有效的邮箱配置，请检查config.txt文件")
            return

        print(f"已加载 {len(loaded_accounts)} 个邮箱账户")
        for email in loaded_accounts:
            print(f"- {email}")

        first_email = next(iter(loaded_accounts))

        print(f"\n测试获取 {first_email} 的邮件...")
        messages = await email_manager.get_messages(first_email, 5)

        print(f"\n找到 {len(messages)} 封邮件:")
        for index, message in enumerate(messages, 1):
            subject = message.get("subject", "无主题")
            from_addr = message.get("from", {}).get("emailAddress", {}).get("address", "未知发件人")
            print(f"{index}. {subject} - {from_addr}")

    except Exception as exc:
        logger.error("程序执行出错: %s", exc)
        raise


if __name__ == "__main__":
    import sys

    import uvicorn

    if len(sys.argv) > 1 and sys.argv[1] == "web":
        print("启动Web服务器...")
        print("访问 http://localhost:5001 查看前端界面")
        reload_flag = os.getenv("UVICORN_RELOAD", "")
        reload_enabled = reload_flag.strip().lower() in {"1", "true", "yes", "on"}
        uvicorn.run(
            "app.mail_api:app",
            host="0.0.0.0",
            port=5001,
            log_level="info",
            reload=reload_enabled,
        )
    else:
        asyncio.run(main())
