from typing import Optional
import logging

from fastapi import APIRouter, HTTPException, Request, Response, status

from ..database import db_manager
from ..exceptions import (
    AccountLockedError,
    AuthenticationError,
    InvalidCredentialsError,
)
from ..jwt_auth import (
    ACCESS_TOKEN_EXPIRE_MINUTES,
    decode_access_token,
)
from ..models import (
    AdminLoginRequest,
    AdminLoginResponse,
    AdminProfile,
    ApiResponse,
    LogoutRequest,
    TokenRefreshRequest,
)
from ..rate_limiter import auditor, rate_limiter
from ..services import admin_auth_service
from ..settings import get_settings
from ..utils.request_utils import get_client_ip

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/admin", tags=["管理员认证"])
settings = get_settings()

def _set_refresh_cookie(response: Response, refresh_token: str, max_age: int) -> None:
    """根据配置写入刷新令牌 Cookie（可选）"""
    if not settings.admin_refresh_cookie_enabled:
        return
    response.set_cookie(
        key=settings.admin_refresh_cookie_name,
        value=refresh_token,
        max_age=max_age,
        httponly=True,
        secure=settings.admin_refresh_cookie_secure,
        samesite="strict",
        path=settings.admin_refresh_cookie_path,
    )


@router.post("/login", response_model=AdminLoginResponse)
async def admin_login(
    login_request: AdminLoginRequest,
    request: Request,
    response: Response,
) -> AdminLoginResponse:
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
            raise AccountLockedError(
                message=f"登录失败次数过多,请在 {remaining_seconds} 秒后重试",
                lockout_remaining=remaining_seconds
            )

        # 2. 验证用户名和密码（数据库管理员）
        admin = await admin_auth_service.authenticate(username, login_request.password)

        # 3. 认证成功
        await rate_limiter.record_attempt(client_ip, username, True)
        await auditor.log_attempt(client_ip, username, True)

        # 创建 Token 对
        token_pair = await admin_auth_service.issue_token_pair(
            admin=admin,
            user_agent=request.headers.get("user-agent"),
            ip_address=client_ip,
        )

        _set_refresh_cookie(response, token_pair["refresh_token"], token_pair["refresh_expires_in"])

        logger.info(f"管理员登录成功: 用户名={username}, IP={client_ip}")

        return AdminLoginResponse(
            access_token=token_pair["access_token"],
            refresh_token=token_pair["refresh_token"],
            token_type="bearer",
            expires_in=token_pair["expires_in"],
            refresh_expires_in=token_pair["refresh_expires_in"],
            user=AdminProfile(
                id=admin["id"],
                username=admin["username"],
                role=admin.get("role", "admin"),
                is_active=bool(admin.get("is_active", True)),
            ),
        )

    except (HTTPException, AccountLockedError, InvalidCredentialsError):
        raise
    except Exception as e:
        logger.error(f"管理员登录异常: {e}")
        await auditor.log_attempt(client_ip, username, False, f"系统错误: {str(e)}")
        raise AuthenticationError(message="登录失败，请稍后重试")


@router.post("/refresh", response_model=AdminLoginResponse)
async def refresh_token(
    request: Request,
    response: Response,
    refresh_request: TokenRefreshRequest,
) -> AdminLoginResponse:
    """刷新访问令牌"""
    refresh_token = refresh_request.refresh_token or request.cookies.get(settings.admin_refresh_cookie_name)
    if not refresh_token:
        raise AuthenticationError(message="缺少刷新令牌")

    client_ip = get_client_ip(request)
    try:
        token_pair = await admin_auth_service.rotate_refresh_token(
            refresh_token=refresh_token,
            user_agent=request.headers.get("user-agent"),
            ip_address=client_ip,
        )
        _set_refresh_cookie(response, token_pair["refresh_token"], token_pair["refresh_expires_in"])

        token_payload = decode_access_token(token_pair["access_token"])
        if not token_payload:
            raise AuthenticationError(message="令牌无效")

        admin_id = token_payload.get("admin_id")
        admin = await db_manager.get_admin_by_id(admin_id) if admin_id is not None else None
        if not admin:
            raise AuthenticationError(message="账号不存在或不可用")

        return AdminLoginResponse(
            access_token=token_pair["access_token"],
            refresh_token=token_pair["refresh_token"],
            token_type="bearer",
            expires_in=token_pair["expires_in"],
            refresh_expires_in=token_pair["refresh_expires_in"],
            user=AdminProfile(
                id=int(admin["id"]),
                username=admin["username"],
                role=admin.get("role", "admin"),
                is_active=bool(admin.get("is_active", True)),
            ),
        )
    except (HTTPException, AuthenticationError):
        raise
    except Exception as e:
        logger.error(f"刷新令牌失败: {e}")
        raise AuthenticationError(message="刷新失败")


@router.post("/logout", response_model=ApiResponse)
async def admin_logout(request: Request, payload: LogoutRequest, response: Response) -> ApiResponse:
    """注销并撤销刷新令牌"""
    refresh_token = payload.refresh_token or request.cookies.get(settings.admin_refresh_cookie_name)
    if not refresh_token:
        return ApiResponse(success=True, message="已退出")

    try:
        await admin_auth_service.revoke_refresh_token(refresh_token)
    finally:
        if settings.admin_refresh_cookie_enabled:
            response.delete_cookie(
                key=settings.admin_refresh_cookie_name,
                path=settings.admin_refresh_cookie_path,
            )
    return ApiResponse(success=True, message="已退出")
