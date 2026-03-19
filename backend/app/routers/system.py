import logging
import time
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status

from ..core.decorators import handle_exceptions
from ..core.exceptions import DatabaseError
from ..core.metrics import api_metrics, get_metrics, get_metrics_content_type
from ..db import db_manager
from ..dependencies import (
    AdminUser,
    DbManager,
    EmailMgr,
    get_db_manager,
    get_email_manager,
)
from ..models import ApiResponse, SystemConfigBatchUpdate, SystemConfigRequest
from ..services.channeling.channel_stats_service import get_channel_stats
from ..services import (
    load_system_config,
    set_system_config_value,
)
from ..settings import get_settings
from ..version import __version__ as APP_VERSION

logger = logging.getLogger(__name__)

router = APIRouter(tags=["系统配置"])
settings = get_settings()

_startup_time = datetime.now(UTC)

METRICS_ALLOWED_IPS = {"127.0.0.1", "::1", "localhost"}


# ============================================================================
# Health Check Endpoints (no admin auth required)
# ============================================================================


@router.get("/api/health")
async def basic_health_check() -> dict:
    """基础健康检查（用于负载均衡器）"""
    try:
        db_ok = await db_manager.check_database_connection()
    except Exception:
        db_ok = False
    return {
        "status": "healthy" if db_ok else "degraded",
        "version": APP_VERSION,
        "timestamp": datetime.now(UTC).isoformat() + "Z",
        "components": {
            "database": "healthy" if db_ok else "unhealthy",
        },
    }


@router.get("/api/health/detailed")
async def detailed_health_check(
    db=Depends(get_db_manager),
    email_mgr=Depends(get_email_manager),
) -> dict:
    """详细健康检查端点。返回所有子系统的健康状态。"""
    checks: dict[str, Any] = {}
    overall_healthy = True

    try:
        db_health = await _check_database_health(db)
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
        logger.error("Database health check failed: %s", e)
        checks["database"] = {"status": "unhealthy", "error": "Internal error"}
        overall_healthy = False

    try:
        email_ready = email_mgr.is_ready() if hasattr(email_mgr, "is_ready") else True
        email_metrics = await email_mgr.get_metrics()
        checks["email_service"] = {
            "status": "healthy" if email_ready else "degraded",
            "accounts_loaded": email_metrics.get("accounts_count", 0),
            "cache_hit_rate": email_metrics.get("cache_hit_rate"),
        }
    except Exception as e:
        logger.error("Email service health check failed: %s", e)
        checks["email_service"] = {"status": "unhealthy", "error": "Internal error"}

    try:
        cache_stats = await _check_cache_health(db)
        checks["email_cache"] = {"status": "healthy", **cache_stats}
    except Exception as e:
        logger.error("Email cache health check failed: %s", e)
        checks["email_cache"] = {"status": "unhealthy", "error": "Internal error"}

    uptime_seconds = (datetime.now(UTC) - _startup_time).total_seconds()

    return {
        "status": "healthy" if overall_healthy else "degraded",
        "version": APP_VERSION,
        "environment": settings.app_env,
        "timestamp": datetime.now(UTC).isoformat() + "Z",
        "uptime_seconds": round(uptime_seconds, 2),
        "checks": checks,
    }


@router.get("/api/health/ready")
async def readiness_check(
    response: Response,
    db=Depends(get_db_manager),
    email_mgr=Depends(get_email_manager),
) -> dict:
    """就绪检查（用于 Kubernetes readinessProbe）。"""
    try:
        db_health = await _check_database_health(db)
        db_ok = db_health.get("connected", False)
        email_ok = email_mgr.is_ready() if hasattr(email_mgr, "is_ready") else True

        if db_ok and email_ok:
            return {"status": "ready", "timestamp": datetime.now(UTC).isoformat() + "Z"}
        else:
            response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
            return {
                "status": "not_ready",
                "message": "service not ready",
                "timestamp": datetime.now(UTC).isoformat() + "Z",
                "database": "ok" if db_ok else "failed",
                "email_service": "ok" if email_ok else "failed",
            }
    except Exception as e:
        logger.error("Readiness check failed: %s", e)
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return {
            "status": "not_ready",
            "timestamp": datetime.now(UTC).isoformat() + "Z",
            "error": "Internal error",
        }


@router.get("/api/health/live")
async def liveness_check() -> dict:
    """存活检查（用于 Kubernetes livenessProbe）。仅检查应用进程是否响应。"""
    return {"status": "alive", "timestamp": datetime.now(UTC).isoformat() + "Z"}


async def _check_database_health(db) -> dict[str, Any]:
    start = time.time()
    try:
        result = await db.check_database_connection()
        latency_ms = (time.time() - start) * 1000
        return {"connected": result, "latency_ms": round(latency_ms, 2)}
    except Exception as e:
        logger.error("Database health check error: %s", e)
        return {"connected": False, "error": "Internal error"}


async def _check_cache_health(db) -> dict[str, Any]:
    stats = await db.get_email_cache_stats()
    return {
        "total_cached_emails": stats.get("total_messages", 0),
        "accounts_with_cache": stats.get("cached_accounts", 0),
    }


# ============================================================================
# System Config (admin auth required)
# ============================================================================


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

    success = await set_system_config_value("email_limit", request.email_limit)
    if success:
        return ApiResponse(
            success=True,
            message=f"系统配置更新成功，邮件限制设置为 {request.email_limit}",
        )
    else:
        raise DatabaseError(message="保存系统配置失败")


@router.put("/api/system/config")
@handle_exceptions("批量更新系统配置")
async def batch_update_system_config(
    admin: AdminUser,
    request: SystemConfigBatchUpdate,
) -> ApiResponse:
    """批量更新系统配置（需要管理员认证）"""
    from ..services.constants import SYSTEM_CONFIG_DEFAULTS

    updated = {}
    errors = []
    for key, value in request.configs.items():
        if key not in SYSTEM_CONFIG_DEFAULTS:
            errors.append(f"未知配置项: {key}")
            continue
        ok = await set_system_config_value(key, value)
        if ok:
            config = await load_system_config()
            updated[key] = config.get(key, value)
        else:
            errors.append(f"保存失败: {key}")

    msg = f"已更新 {len(updated)} 项配置"
    if errors:
        msg += f"，{len(errors)} 项失败"

    return ApiResponse(
        success=len(updated) > 0 or len(errors) == 0,
        message=msg,
        data={"updated": updated, "errors": errors},
    )


@router.post("/api/system/cache/refresh")
@handle_exceptions("刷新缓存")
async def refresh_cache(
    admin: AdminUser, db: DbManager, email_mgr: EmailMgr
) -> ApiResponse:
    """清空邮件缓存并刷新账户缓存（需要管理员认证）"""
    await email_mgr.invalidate_accounts_cache()
    await db.reset_email_cache()
    await db.upsert_system_metric(
        "cache_reset_at",
        {"timestamp": datetime.now(UTC).isoformat() + "Z"},
    )
    return ApiResponse(success=True, message="缓存已刷新")


# ============================================================================
# Metrics
# ============================================================================


@router.get("/api/system/metrics", tags=["系统管理"])
@handle_exceptions("获取系统指标")
async def get_system_metrics_main(
    admin: AdminUser, db: DbManager, email_mgr: EmailMgr
) -> ApiResponse:
    """获取系统运行指标（需要管理员认证）"""
    metrics = await email_mgr.get_metrics()
    db_metrics = await db.get_all_system_metrics()
    channeling_metrics = await get_channel_stats(None)

    warning = None
    if metrics.get("accounts_source") == "file":
        warning = "账户目前从 config.txt 文件加载，建议导入数据库以获得完整功能。"

    return ApiResponse(
        success=True,
        data={
            "email_manager": metrics,
            "database": db_metrics,
            "outlook_channeling": channeling_metrics,
            "warning": warning,
        },
    )


@router.get("/api/system/metrics/api", tags=["系统管理"])
@handle_exceptions("获取 API 指标")
async def get_api_metrics(admin: AdminUser) -> ApiResponse:
    """获取 API 性能指标（需要管理员认证）"""
    stats = api_metrics.get_stats()
    return ApiResponse(
        success=True,
        data={
            "endpoints": stats,
            "total_requests": sum(s["request_count"] for s in stats.values()),
            "total_errors": sum(s["error_count"] for s in stats.values()),
        },
    )


@router.post("/api/system/metrics/reset", tags=["系统管理"])
@handle_exceptions("重置 API 指标")
async def reset_api_metrics(admin: AdminUser) -> ApiResponse:
    """重置 API 性能指标（需要管理员认证）"""
    api_metrics.reset()
    return ApiResponse(success=True, message="指标已重置")


@router.get("/api/metrics", tags=["监控"])
async def prometheus_metrics(request: Request):
    """Prometheus 指标端点（仅限内部访问）"""
    client_ip = request.client.host if request.client else "unknown"

    if settings.is_production:
        if not _is_allowed_metrics_access(client_ip):
            raise HTTPException(status_code=403, detail="Access denied to metrics endpoint")

    return Response(content=get_metrics(), media_type=get_metrics_content_type())


# ============================================================================
# Audit Events
# ============================================================================


@router.get("/api/audit/events", tags=["审计日志"])
@handle_exceptions("获取审计日志")
async def get_audit_events_api(
    admin: AdminUser,
    db: DbManager,
    event_type: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> ApiResponse:
    """获取审计日志（分页 + 可选类型筛选）"""
    events = await db.get_audit_events(
        event_type=event_type, limit=min(limit, 200), offset=offset
    )
    return ApiResponse(
        success=True, data={"events": events, "limit": limit, "offset": offset}
    )


# ============================================================================
# Extraction Rules
# ============================================================================


@router.get("/api/system/rules", tags=["提取规则"])
@handle_exceptions("获取提取规则")
async def get_extraction_rules(admin: AdminUser, db: DbManager) -> ApiResponse:
    rules = await db.get_all_extraction_rules()
    return ApiResponse(success=True, data=rules)


@router.post("/api/system/rules", tags=["提取规则"])
@handle_exceptions("保存提取规则")
async def save_extraction_rule(
    admin: AdminUser, db: DbManager, request: dict
) -> ApiResponse:
    rule_id = await db.upsert_extraction_rule(
        rule_id=request.get("id"),
        name=request.get("name", ""),
        sender_filter=request.get("sender_filter", ""),
        subject_filter=request.get("subject_filter", ""),
        regex_pattern=request.get("regex_pattern", ""),
        priority=request.get("priority", 0),
        is_active=request.get("is_active", True),
    )
    return ApiResponse(success=True, data={"id": rule_id}, message="规则已保存")


@router.delete("/api/system/rules/{rule_id}", tags=["提取规则"])
@handle_exceptions("删除提取规则")
async def delete_extraction_rule(
    rule_id: int, admin: AdminUser, db: DbManager
) -> ApiResponse:
    ok = await db.delete_extraction_rule(rule_id)
    if ok:
        return ApiResponse(success=True, message="规则已删除")
    return ApiResponse(success=False, message="规则不存在")


def _is_allowed_metrics_access(ip: str) -> bool:
    if ip in METRICS_ALLOWED_IPS:
        return True
    if ip.startswith(
        (
            "10.", "172.16.", "172.17.", "172.18.", "172.19.",
            "172.20.", "172.21.", "172.22.", "172.23.", "172.24.",
            "172.25.", "172.26.", "172.27.", "172.28.", "172.29.",
            "172.30.", "172.31.", "192.168.",
        )
    ):
        return True
    return False
