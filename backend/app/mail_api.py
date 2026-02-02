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
from fastapi.responses import FileResponse, JSONResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles
from sentry_sdk.integrations.fastapi import FastApiIntegration
from sentry_sdk.integrations.starlette import StarletteIntegration

from .core.exceptions import AppException
from .core.middleware import MetricsMiddleware
from .core.startup import log_startup_info, validate_environment

# 导入自定义模块
from .db import db_manager
from .models import ApiResponse
from .routers import accounts, auth, emails, public_accounts, system
from .services import admin_auth_service, email_manager, load_accounts_config
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
        # Performance Monitoring
        traces_sample_rate=0.1 if settings.is_production else 1.0,
        # Set profiles_sample_rate to profile requests
        profiles_sample_rate=0.1 if settings.is_production else 1.0,
    )
    logger.info("Sentry error tracking initialized")

ALLOWED_ORIGINS = settings.allowed_origins
PROJECT_ROOT = Path(__file__).resolve().parents[2]
STATIC_DIR = (PROJECT_ROOT / settings.static_dir).resolve()

# ============================================================================
# FastAPI应用和API端点
# ============================================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用程序生命周期管理"""
    logger.info("启动邮件管理系统...")

    # 记录启动信息
    log_startup_info()

    # 验证环境配置
    warnings = validate_environment()
    for warning in warnings:
        logger.warning(f"[配置警告] {warning}")

    # 生产环境关键配置安全检查
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
    # 引导默认管理员（基于环境变量）
    try:
        await admin_auth_service.bootstrap_default_admin()
    except Exception as exc:
        logger.error("初始化默认管理员失败: %s", exc)
    yield
    logger.info("正在关闭邮件管理系统...")
    try:
        await email_manager.cleanup_all()
        db_manager.close()
    except Exception as e:
        logger.error(f"清理系统资源时出错: {e}")
    logger.info("邮件管理系统已关闭")

app = FastAPI(
    title="Outlook 邮件管理系统",
    description="基于 FastAPI + React 的现代化邮件管理系统",
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

# 添加监控中间件
app.add_middleware(MetricsMiddleware)

# 挂载API路由
app.include_router(auth.router)
app.include_router(accounts.router)
app.include_router(emails.router)
app.include_router(system.router)
app.include_router(public_accounts.router)

# 添加验证错误处理器
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    logger.error(f"Pydantic验证错误: {exc}")
    return JSONResponse(
        status_code=422,
        content=ApiResponse(
            success=False,
            message="数据验证失败",
            error_code="VALIDATION_ERROR",
            data={"details": exc.errors()}
        ).model_dump()
    )


# 添加自定义异常处理器
@app.exception_handler(AppException)
async def app_exception_handler(request: Request, exc: AppException):
    """统一处理应用自定义异常"""
    logger.warning(f"应用异常: {exc.error_code} - {exc.message}")
    return JSONResponse(
        status_code=exc.status_code,
        content=ApiResponse(
            success=False,
            message=exc.message,
            error_code=exc.error_code,
            data=exc.details if exc.details else None
        ).model_dump()
    )


# ============================================================================
# 静态文件与SPA路由
# ============================================================================

# 挂载静态资源 (JS/CSS/Images)
static_assets_path = STATIC_DIR / "assets"
if static_assets_path.exists():
    app.mount("/assets", StaticFiles(directory=static_assets_path), name="assets")
else:
    logger.warning("%s 目录不存在，前端可能未构建", static_assets_path)

# 挂载其他静态文件 (如favicon, images等)
# 注意：这会把 static 目录下的所有文件暴露在 /static/ 下
if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
else:
    logger.warning("静态目录 %s 不存在", STATIC_DIR)

@app.get("/{full_path:path}", include_in_schema=False)
async def serve_spa(full_path: str):
    """SPA Catch-all路由"""
    # API请求不处理
    if full_path.startswith("api/") or full_path.startswith("docs") or full_path.startswith("redoc"):
         raise HTTPException(status_code=404, detail="Not Found")

    # 尝试返回index.html (SPA入口)
    index_path = STATIC_DIR / "index.html"
    if index_path.exists():
        return FileResponse(index_path)
    else:
        return PlainTextResponse("Frontend not built. Please run 'npm run build' in frontend directory.", status_code=503)

# ============================================================================
# 命令行入口
# ============================================================================

async def main():
    """命令行模式入口"""
    try:
        accounts = await load_accounts_config()
        if not accounts:
            print("没有找到有效的邮箱配置，请检查config.txt文件")
            return

        print(f"已加载 {len(accounts)} 个邮箱账户")
        for email in accounts.keys():
            print(f"- {email}")

        # 测试第一个账户
        first_email = list(accounts.keys())[0]

        print(f"\n测试获取 {first_email} 的邮件...")
        messages = await email_manager.get_messages(first_email, 5)

        print(f"\n找到 {len(messages)} 封邮件:")
        for i, msg in enumerate(messages, 1):
            subject = msg.get('subject', '无主题')
            from_addr = msg.get('from', {}).get('emailAddress', {}).get('address', '未知发件人')
            print(f"{i}. {subject} - {from_addr}")

    except Exception as e:
        logger.error(f"程序执行出错: {e}")
        raise

if __name__ == '__main__':
    import sys

    import uvicorn

    if len(sys.argv) > 1 and sys.argv[1] == 'web':
        # Web模式
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
        # 命令行模式
        asyncio.run(main())
