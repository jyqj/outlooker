from datetime import datetime
import logging
from fastapi import APIRouter, HTTPException, Header, Depends
from typing import Optional

from ..models import ApiResponse, SystemConfigRequest
from ..dependencies import AdminUser

logger = logging.getLogger(__name__)
from ..exceptions import ServiceUnavailableError, ValidationError, DatabaseError
from ..jwt_auth import get_current_admin
from ..settings import get_settings
from ..services import (
    load_system_config,
    set_system_config_value,
    email_manager,
    db_manager,
)
from ..version import __version__ as APP_VERSION

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
            "error": str(e),
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
async def get_system_config(admin: AdminUser) -> ApiResponse:
    """获取系统配置（需要管理员认证）"""
    try:
        config = await load_system_config()
        return ApiResponse(success=True, data=config)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取系统配置失败: {e}")
        raise DatabaseError(message="获取系统配置失败")

@router.post("/api/system/config")
async def update_system_config(admin: AdminUser, request: SystemConfigRequest) -> ApiResponse:
    """更新系统配置（需要管理员认证）"""
    try:
        if request.email_limit < 1 or request.email_limit > 50:
            return ApiResponse(success=False, message="邮件限制必须在1-50之间")
        
        success = await set_system_config_value('email_limit', request.email_limit)
        if success:
            return ApiResponse(success=True, message=f"系统配置更新成功，邮件限制设置为 {request.email_limit}")
        else:
            raise DatabaseError(message="保存系统配置失败")
    except (HTTPException, ValidationError, DatabaseError):
        raise
    except Exception as e:
        logger.error(f"更新系统配置失败: {e}")
        raise DatabaseError(message="更新系统配置失败")


@router.get("/api/system/metrics")
async def get_system_metrics(admin: AdminUser) -> ApiResponse:
    """获取系统运行指标（需要管理员认证）"""
    try:
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
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取系统指标失败: {e}")
        raise DatabaseError(message="获取系统指标失败")


@router.post("/api/system/cache/refresh")
async def refresh_cache(admin: AdminUser) -> ApiResponse:
    """清空邮件缓存并刷新账户缓存（需要管理员认证）"""
    try:
        await email_manager.invalidate_accounts_cache()
        await db_manager.reset_email_cache()
        await db_manager.upsert_system_metric(
            "cache_reset_at",
            {"timestamp": datetime.utcnow().isoformat() + "Z"},
        )
        return ApiResponse(success=True, message="缓存已刷新")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"刷新缓存失败: {e}")
        raise DatabaseError(message="刷新缓存失败")
