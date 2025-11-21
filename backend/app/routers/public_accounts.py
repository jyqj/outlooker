from fastapi import APIRouter, Depends, HTTPException, Request

from ..config import logger, INBOX_FOLDER_NAME
from ..messages import INFO_NO_MESSAGES
from ..models import ApiResponse
from ..services import (
    db_manager,
    email_manager,
    extract_code_from_message,
)
from ..rate_limiter import public_api_rate_limiter


router = APIRouter(prefix="/api/public", tags=["公共邮箱接口"])


async def enforce_public_rate_limit(request: Request) -> None:
    """按 IP 施加速率限制，防止公共接口被滥用"""
    client_ip = request.client.host if request.client else "unknown"
    allowed, retry_after = await public_api_rate_limiter.is_allowed(client_ip)
    if not allowed:
        detail = "请求过于频繁，请稍后重试"
        if retry_after:
            detail = f"请求过于频繁，请在 {retry_after} 秒后重试"
        raise HTTPException(status_code=429, detail=detail)


@router.get("/account-unused")
async def get_unused_account(_: None = Depends(enforce_public_rate_limit)) -> ApiResponse:
    """获取一个尚未使用的邮箱账户

    - 不需要管理员认证
    - 按创建时间最早的未使用账户返回
    """
    try:
        email = await db_manager.get_first_unused_account_email()
        if not email:
            return ApiResponse(success=False, message="暂无未使用的邮箱")

        return ApiResponse(
            success=True,
            data={"email": email},
            message="获取未使用邮箱成功",
        )
    except Exception as exc:
        logger.error("获取未使用邮箱失败: %s", exc)
        return ApiResponse(success=False, message="获取未使用邮箱失败")


@router.post("/account/{email}/used")
async def mark_account_used_public(
    email: str,
    _: None = Depends(enforce_public_rate_limit),
) -> ApiResponse:
    """将指定邮箱标记为已使用

    - 不需要管理员认证
    - 主要用于自助接码流程中，将已分配过的邮箱标记为“已用”
    """
    email = (email or "").strip()
    if not email:
        return ApiResponse(success=False, message="邮箱地址不能为空")

    try:
        exists = await db_manager.account_exists(email)
        if not exists:
            return ApiResponse(success=False, message="账户不存在")

        success = await db_manager.mark_account_used(email)
        if not success:
            return ApiResponse(success=False, message="标记账户为已使用失败")

        logger.info("账户已标记为已使用: %s", email)
        return ApiResponse(
            success=True,
            message="账户已标记为已使用",
            data={"email": email},
        )
    except Exception as exc:
        logger.error("标记账户为已使用失败(%s): %s", email, exc)
        return ApiResponse(success=False, message="标记账户为已使用失败")


@router.delete("/account/{email}")
async def delete_account_public(
    email: str,
    _: None = Depends(enforce_public_rate_limit),
) -> ApiResponse:
    """删除指定邮箱账户

    - 不需要管理员认证
    - 同时会删除关联的标签和邮件缓存
    """
    email = (email or "").strip()
    if not email:
        return ApiResponse(success=False, message="邮箱地址不能为空")

    try:
        deleted = await db_manager.delete_account(email)
        if not deleted:
            return ApiResponse(success=False, message="账户不存在或删除失败")

        # 删除账户后刷新邮件管理器缓存
        await email_manager.invalidate_accounts_cache()

        logger.info("通过公共接口删除账户: %s", email)
        return ApiResponse(
            success=True,
            message="账户已删除",
            data={"email": email},
        )
    except Exception as exc:
        logger.error("通过公共接口删除账户失败(%s): %s", email, exc)
        return ApiResponse(success=False, message="删除账户失败")


@router.get("/account/{email}/otp")
async def get_latest_otp(
    email: str,
    _: None = Depends(enforce_public_rate_limit),
) -> ApiResponse:
    """获取指定邮箱最新一封邮件的验证码（接码）

    - 不需要管理员认证
    - 只返回验证码本身；如解析失败则返回原因
    """
    email = (email or "").strip()
    if not email:
        return ApiResponse(success=False, message="邮箱地址不能为空")

    try:
        # 尝试获取最新一封邮件
        messages = await email_manager.get_messages(email, top=1, folder=None)
        if not messages:
            return ApiResponse(success=False, message=INFO_NO_MESSAGES)

        latest = messages[0]
        code = extract_code_from_message(latest)

        if not code:
            return ApiResponse(success=False, message="未自动识别到验证码")

        return ApiResponse(
            success=True,
            data={"code": code},
            message="验证码解析成功",
        )
    except Exception as exc:
        logger.error("获取验证码失败(%s): %s", email, exc)
        return ApiResponse(success=False, message="获取验证码失败")


