import logging
from datetime import datetime

from fastapi import APIRouter

from ..core.decorators import handle_exceptions
from ..core.exceptions import DatabaseError, ServiceUnavailableError
from ..core.metrics import api_metrics
from ..dependencies import AdminUser
from ..models import ApiResponse, SystemConfigRequest
from ..services import (
    db_manager,
    email_manager,
    load_system_config,
    set_system_config_value,
)
from ..settings import get_settings
from ..version import __version__ as APP_VERSION

logger = logging.getLogger(__name__)

router = APIRouter(tags=["系统配置"])
settings = get_settings()


@router.get("/api/health")
async def health_check() -> dict:
    """
    Health check endpoint for monitoring and load balancers.
    
    Returns basic health status without authentication.
    """
    try:
        # Check database connectivity
        db_healthy = await db_manager.check_database_connection()

        # Check if email manager is ready
        email_service_ready = email_manager.is_ready() if hasattr(email_manager, 'is_ready') else True

        # Overall status
        is_healthy = db_healthy and email_service_ready

        return {
            "status": "healthy" if is_healthy else "degraded",
            "version": APP_VERSION,
            "environment": settings.app_env,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "components": {
                "database": "healthy" if db_healthy else "unhealthy",
                "email_service": "healthy" if email_service_ready else "degraded",
            }
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {
            "status": "unhealthy",
            "version": APP_VERSION,
            "environment": settings.app_env,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "error": "internal_error",  # 不暴露具体异常文本
        }


@router.get("/api/health/ready")
async def readiness_check() -> dict:
    """
    Readiness probe for Kubernetes/container orchestration.
    
    Checks if the application is ready to receive traffic.
    """
    try:
        db_healthy = await db_manager.check_database_connection()

        if not db_healthy:
            raise ServiceUnavailableError(message="Database not ready")

        return {"status": "ready", "timestamp": datetime.utcnow().isoformat() + "Z"}
    except ServiceUnavailableError:
        raise
    except Exception as e:
        raise ServiceUnavailableError(message=f"Not ready: {str(e)}")


@router.get("/api/health/live")
async def liveness_check() -> dict:
    """
    Liveness probe for Kubernetes/container orchestration.
    
    Simple check to verify the application is running.
    """
    return {"status": "alive", "timestamp": datetime.utcnow().isoformat() + "Z"}

@router.get("/api/system/config")
@handle_exceptions("获取系统配置")
async def get_system_config(admin: AdminUser) -> ApiResponse:
    """获取系统配置（需要管理员认证）"""
    config = await load_system_config()
    return ApiResponse(success=True, data=config)

@router.post("/api/system/config")
@handle_exceptions("更新系统配置")
async def update_system_config(admin: AdminUser, request: SystemConfigRequest) -> ApiResponse:
    """更新系统配置（需要管理员认证）"""
    if request.email_limit < 1 or request.email_limit > 50:
        return ApiResponse(success=False, message="邮件限制必须在1-50之间")

    success = await set_system_config_value('email_limit', request.email_limit)
    if success:
        return ApiResponse(success=True, message=f"系统配置更新成功，邮件限制设置为 {request.email_limit}")
    else:
        raise DatabaseError(message="保存系统配置失败")


@router.get("/api/system/metrics/system")
@handle_exceptions("获取系统指标")
async def get_system_metrics(admin: AdminUser) -> ApiResponse:
    """获取系统运行指标（需要管理员认证）"""
    metrics = await email_manager.get_metrics()
    db_metrics = await db_manager.get_all_system_metrics()

    warning = None
    if metrics.get("accounts_source") == "file":
        warning = "账户目前从 config.txt 文件加载，建议导入数据库以获得完整功能。"

    return ApiResponse(success=True, data={
        "email_manager": metrics,
        "database": db_metrics,
        "warning": warning
    })


@router.post("/api/system/cache/refresh")
@handle_exceptions("刷新缓存")
async def refresh_cache(admin: AdminUser) -> ApiResponse:
    """清空邮件缓存并刷新账户缓存（需要管理员认证）"""
    await email_manager.invalidate_accounts_cache()
    await db_manager.reset_email_cache()
    await db_manager.upsert_system_metric(
        "cache_reset_at",
        {"timestamp": datetime.utcnow().isoformat() + "Z"},
    )
    return ApiResponse(success=True, message="缓存已刷新")


@router.get("/api/system/metrics", tags=["系统管理"])
@handle_exceptions("获取系统指标")
async def get_system_metrics_main(admin: AdminUser) -> ApiResponse:
    """获取系统运行指标（需要管理员认证）
    
    返回系统运行指标，包括：
    - email_manager: 邮件管理器指标
    - database: 数据库指标
    """
    metrics = await email_manager.get_metrics()
    db_metrics = await db_manager.get_all_system_metrics()

    warning = None
    if metrics.get("accounts_source") == "file":
        warning = "账户目前从 config.txt 文件加载，建议导入数据库以获得完整功能。"

    return ApiResponse(success=True, data={
        "email_manager": metrics,
        "database": db_metrics,
        "warning": warning
    })


@router.get("/api/system/metrics/api", tags=["系统管理"])
@handle_exceptions("获取 API 指标")
async def get_api_metrics(admin: AdminUser) -> ApiResponse:
    """获取 API 性能指标（需要管理员认证）
    
    返回所有 API 端点的请求统计信息，包括：
    - 请求次数
    - 错误次数和错误率
    - 平均/最小/最大响应时间
    """
    stats = api_metrics.get_stats()
    return ApiResponse(
        success=True,
        data={
            "endpoints": stats,
            "total_requests": sum(s["request_count"] for s in stats.values()),
            "total_errors": sum(s["error_count"] for s in stats.values()),
        }
    )


@router.post("/api/system/metrics/reset", tags=["系统管理"])
@handle_exceptions("重置 API 指标")
async def reset_api_metrics(admin: AdminUser) -> ApiResponse:
    """重置 API 性能指标（需要管理员认证）"""
    api_metrics.reset()
    return ApiResponse(success=True, message="指标已重置")
