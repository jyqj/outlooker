from datetime import datetime
from fastapi import APIRouter, HTTPException, Header, Depends
from typing import Optional

from ..models import ApiResponse, SystemConfigRequest
from ..config import logger, DEFAULT_EMAIL_LIMIT
from ..jwt_auth import get_current_admin
from ..services import (
    load_system_config,
    set_system_config_value,
    email_manager,
    db_manager,
)

router = APIRouter(tags=["系统配置"])

@router.get("/api/system/config")
async def get_system_config(authorization: Optional[str] = Header(None)) -> ApiResponse:
    """获取系统配置（需要管理员认证）"""
    try:
        _ = get_current_admin(authorization)
        config = await load_system_config()
        return ApiResponse(success=True, data=config)
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"获取系统配置失败: {e}")
        return ApiResponse(success=False, message="获取系统配置失败")

@router.post("/api/system/config")
async def update_system_config(request: SystemConfigRequest, authorization: Optional[str] = Header(None)) -> ApiResponse:
    """更新系统配置（需要管理员认证）"""
    try:
        _ = get_current_admin(authorization)

        if request.email_limit < 1 or request.email_limit > 50:
            return ApiResponse(success=False, message="邮件限制必须在1-50之间")
        
        success = await set_system_config_value('email_limit', request.email_limit)
        if success:
            return ApiResponse(success=True, message=f"系统配置更新成功，邮件限制设置为 {request.email_limit}")
        else:
            return ApiResponse(success=False, message="保存系统配置失败")
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"更新系统配置失败: {e}")
        return ApiResponse(success=False, message="更新系统配置失败")


@router.get("/api/system/metrics")
async def get_system_metrics(authorization: Optional[str] = Header(None)) -> ApiResponse:
    """获取系统运行指标（需要管理员认证）"""
    try:
        _ = get_current_admin(authorization)
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
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"获取系统指标失败: {e}")
        return ApiResponse(success=False, message="获取系统指标失败")


@router.post("/api/system/cache/refresh")
async def refresh_cache(authorization: Optional[str] = Header(None)) -> ApiResponse:
    """清空邮件缓存并刷新账户缓存（需要管理员认证）"""
    try:
        _ = get_current_admin(authorization)
        await email_manager.invalidate_accounts_cache()
        await db_manager.reset_email_cache()
        await db_manager.upsert_system_metric(
            "cache_reset_at",
            {"timestamp": datetime.utcnow().isoformat() + "Z"},
        )
        return ApiResponse(success=True, message="缓存已刷新")
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"刷新缓存失败: {e}")
        return ApiResponse(success=False, message="刷新缓存失败")
