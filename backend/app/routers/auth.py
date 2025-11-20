from fastapi import APIRouter, HTTPException, Depends, Request
from pydantic import BaseModel
from typing import Optional

from ..jwt_auth import (
    authenticate_admin, create_access_token,
    verify_legacy_token, ACCESS_TOKEN_EXPIRE_MINUTES
)
from ..models import AdminLoginRequest, AdminLoginResponse, AdminTokenRequest, ApiResponse
from ..config import logger
from ..rate_limiter import rate_limiter, auditor

router = APIRouter(prefix="/api/admin", tags=["管理员认证"])

def get_client_ip(request: Request) -> str:
    """获取客户端真实 IP 地址

    优先从 X-Forwarded-For 或 X-Real-IP 头获取(适配反向代理)
    否则使用直连 IP
    """
    # 检查反向代理头
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        # X-Forwarded-For 可能包含多个 IP,取第一个
        return forwarded.split(",")[0].strip()

    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip.strip()

    # 使用直连 IP
    if request.client:
        return request.client.host

    return "unknown"

def verify_admin_token(token: str) -> bool:
    """验证管理令牌（向后兼容旧的固定 token）"""
    return verify_legacy_token(token)

@router.post("/login", response_model=AdminLoginResponse)
async def admin_login(login_request: AdminLoginRequest, request: Request):
    """管理员登录

    使用用户名和密码登录，返回 JWT token。

    安全特性:
    - 基于 IP + 用户名的频率限制(5分钟内最多5次失败)
    - 失败5次后锁定15分钟
    - 所有登录尝试记录到审计日志

    - **username**: 管理员用户名
    - **password**: 管理员密码

    返回的 token 有效期为 24 小时，需要在后续请求的 Authorization header 中使用：
    ```
    Authorization: Bearer {access_token}
    ```
    """
    client_ip = get_client_ip(request)
    username = login_request.username

    try:
        # 1. 检查是否被锁定
        is_locked, remaining_seconds = await rate_limiter.is_locked_out(client_ip, username)
        if is_locked:
            # 记录审计日志
            await auditor.log_attempt(
                client_ip, username, False,
                f"账户已锁定,剩余{remaining_seconds}秒"
            )
            raise HTTPException(
                status_code=429,
                detail=f"登录失败次数过多,请在 {remaining_seconds} 秒后重试"
            )

        # 2. 验证用户名和密码
        if not authenticate_admin(username, login_request.password):
            # 记录失败尝试
            await rate_limiter.record_attempt(client_ip, username, False)
            await auditor.log_attempt(client_ip, username, False, "用户名或密码错误")

            # 获取当前失败次数
            attempt_count = await rate_limiter.get_attempt_count(client_ip, username)
            remaining_attempts = 5 - attempt_count

            if remaining_attempts > 0:
                detail = f"用户名或密码错误,剩余尝试次数: {remaining_attempts}"
            else:
                detail = "用户名或密码错误,账户已被锁定15分钟"

            raise HTTPException(status_code=401, detail=detail)

        # 3. 认证成功
        # 记录成功尝试(会清除失败记录)
        await rate_limiter.record_attempt(client_ip, username, True)
        await auditor.log_attempt(client_ip, username, True)

        # 创建 JWT token
        access_token = create_access_token(
            data={"sub": username}
        )

        logger.info(f"管理员登录成功: 用户名={username}, IP={client_ip}")

        return AdminLoginResponse(
            access_token=access_token,
            token_type="bearer",
            expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"管理员登录异常: {e}")
        await auditor.log_attempt(client_ip, username, False, f"系统错误: {str(e)}")
        raise HTTPException(status_code=500, detail="登录失败")

@router.post("/verify")
async def admin_verify(request: AdminTokenRequest) -> ApiResponse:
    """验证管理令牌（向后兼容旧的固定 token 方式）
    
    **已废弃**: 建议使用 `/api/admin/login` 获取 JWT token
    """
    try:
        if verify_admin_token(request.token):
            return ApiResponse(success=True, message="验证成功")
        return ApiResponse(success=False, message="令牌无效")
    except Exception as e:
        logger.error(f"验证管理令牌失败: {e}")
        return ApiResponse(success=False, message="验证失败")
