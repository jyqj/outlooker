import logging
import time
from datetime import datetime
from typing import Any

from fastapi import APIRouter, HTTPException, Request, Response, status

from ..core.decorators import handle_exceptions
from ..core.exceptions import DatabaseError, ServiceUnavailableError
from ..core.metrics import api_metrics, get_metrics, get_metrics_content_type
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

# 应用启动时间
_startup_time = datetime.utcnow()

# 允许访问指标的 IP 白名单（可配置）
METRICS_ALLOWED_IPS = {"127.0.0.1", "::1", "localhost"}


@router.get("/api/health")
async def basic_health_check() -> dict:
    """基础健康检查（用于负载均衡器）"""
    return {"status": "healthy", "timestamp": datetime.utcnow().isoformat() + "Z"}


@router.get("/api/health/detailed")
async def detailed_health_check() -> dict:
    """
    详细健康检查端点。
    
    返回所有子系统的健康状态。
    """
    checks: dict[str, Any] = {}
    overall_healthy = True
    
    # 1. 数据库检查
    try:
        db_health = await _check_database_health()
        is_db_healthy = db_health.get("connected", False)
        checks["database"] = {
            "status": "healthy" if is_db_healthy else "unhealthy",
            "latency_ms": db_health.get("latency_ms"),
        }
        if not is_db_healthy:
            overall_healthy = False
            if "error" in db_health:
                checks["database"]["error"] = db_health["error"]
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        checks["database"] = {"status": "unhealthy", "error": "Internal error"}
        overall_healthy = False
    
    # 2. 邮件服务检查
    try:
        email_ready = email_manager.is_ready() if hasattr(email_manager, 'is_ready') else True
        email_metrics = await email_manager.get_metrics()
        checks["email_service"] = {
            "status": "healthy" if email_ready else "degraded",
            "accounts_loaded": email_metrics.get("accounts_count", 0),
            "cache_hit_rate": email_metrics.get("cache_hit_rate"),
        }
    except Exception as e:
        logger.error(f"Email service health check failed: {e}")
        checks["email_service"] = {"status": "unhealthy", "error": "Internal error"}
    
    # 3. 缓存检查
    try:
        cache_stats = await _check_cache_health()
        checks["email_cache"] = {
            "status": "healthy",
            **cache_stats,
        }
    except Exception as e:
        logger.error(f"Email cache health check failed: {e}")
        checks["email_cache"] = {"status": "unhealthy", "error": "Internal error"}
    
    # 4. 计算运行时间
    uptime_seconds = (datetime.utcnow() - _startup_time).total_seconds()
    
    return {
        "status": "healthy" if overall_healthy else "degraded",
        "version": APP_VERSION,
        "environment": settings.app_env,
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "uptime_seconds": round(uptime_seconds, 2),
        "checks": checks,
    }


@router.get("/api/health/ready")
async def readiness_check(response: Response) -> dict:
    """
    就绪检查（用于 Kubernetes readinessProbe）。
    
    检查应用是否准备好接收流量。
    """
    try:
        # 检查数据库连接
        db_health = await _check_database_health()
        db_ok = db_health.get("connected", False)
        
        # 检查邮件服务
        email_ok = email_manager.is_ready() if hasattr(email_manager, 'is_ready') else True
        
        if db_ok and email_ok:
            return {"status": "ready", "timestamp": datetime.utcnow().isoformat() + "Z"}
        else:
            response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
            return {
                "status": "not_ready",
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "database": "ok" if db_ok else "failed",
                "email_service": "ok" if email_ok else "failed",
            }
    except Exception as e:
        logger.error(f"Readiness check failed: {e}")
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return {
            "status": "not_ready",
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "error": "Internal error",
        }


@router.get("/api/health/live")
async def liveness_check() -> dict:
    """
    存活检查（用于 Kubernetes livenessProbe）。
    
    仅检查应用进程是否响应。
    """
    return {"status": "alive", "timestamp": datetime.utcnow().isoformat() + "Z"}


async def _check_database_health() -> dict[str, Any]:
    """检查数据库健康状态"""
    start = time.time()
    try:
        # 执行简单查询
        result = await db_manager.execute_health_check()
        latency_ms = (time.time() - start) * 1000
        
        return {
            "connected": result,
            "latency_ms": round(latency_ms, 2),
        }
    except Exception as e:
        logger.error(f"Database health check error: {e}")
        return {
            "connected": False,
            "error": "Internal error",
        }


async def _check_cache_health() -> dict[str, Any]:
    """检查缓存健康状态"""
    stats = await db_manager.get_email_cache_stats()
    return {
        "total_cached_emails": stats.get("total_messages", 0),
        "accounts_with_cache": stats.get("cached_accounts", 0),
    }

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


@router.get("/api/metrics", tags=["监控"])
async def prometheus_metrics(request: Request):
    """Prometheus 指标端点（仅限内部访问）
    
    返回 Prometheus 格式的应用指标，供监控系统抓取。
    生产环境下仅允许内部 IP 访问。
    """
    client_ip = request.client.host if request.client else "unknown"
    
    # IP 白名单检查（生产环境启用）
    if settings.is_production:
        # 检查是否为内部 IP 或白名单 IP
        if not _is_allowed_metrics_access(client_ip):
            raise HTTPException(
                status_code=403, 
                detail="Access denied to metrics endpoint"
            )
    
    return Response(
        content=get_metrics(),
        media_type=get_metrics_content_type()
    )


def _is_allowed_metrics_access(ip: str) -> bool:
    """检查 IP 是否允许访问指标"""
    # 允许本地访问
    if ip in METRICS_ALLOWED_IPS:
        return True
    # 允许私有 IP 段
    if ip.startswith(("10.", "172.16.", "172.17.", "172.18.", "172.19.",
                      "172.20.", "172.21.", "172.22.", "172.23.", "172.24.",
                      "172.25.", "172.26.", "172.27.", "172.28.", "172.29.",
                      "172.30.", "172.31.", "192.168.")):
        return True
    return False
