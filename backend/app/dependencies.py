from __future__ import annotations

from typing import Annotated, Optional

from fastapi import Depends, Header, HTTPException, Request

from .settings import get_settings
from .rate_limiter import public_api_rate_limiter
from .utils.request_utils import get_client_ip

settings = get_settings()


async def verify_public_token(x_public_token: Optional[str] = Header(None)) -> None:
    """校验公共接口调用口令（X-Public-Token）。"""
    if not x_public_token or x_public_token != settings.public_api_token:
        raise HTTPException(status_code=401, detail="未授权的公共接口访问")


# ============================================================================
# 管理员认证依赖
# ============================================================================


async def get_admin_user(
    authorization: Annotated[Optional[str], Header()] = None
) -> str:
    """获取当前认证的管理员用户名
    
    此依赖可作为路由参数使用，自动验证管理员身份。
    
    用法:
        @router.get("/api/accounts")
        async def get_accounts(admin: AdminUser):
            # admin 是已验证的管理员用户名
            ...
    
    Raises:
        HTTPException: 认证失败时抛出 401 错误
    """
    # 延迟导入避免循环依赖
    from .jwt_auth import get_current_admin
    return get_current_admin(authorization)


# 类型别名，用于路由函数参数
AdminUser = Annotated[str, Depends(get_admin_user)]


async def enforce_public_rate_limit(request: Request, email: Optional[str] = None) -> None:
    """按 IP（可选按 IP+email）施加速率限制，防止公共接口被滥用。"""
    client_ip = get_client_ip(request)
    key = client_ip
    if email:
        key = f"{client_ip}:{email.strip().lower()}"

    allowed, retry_after = await public_api_rate_limiter.is_allowed(key)
    if allowed:
        return

    detail = "请求过于频繁，请稍后重试"
    if retry_after:
        detail = f"请求过于频繁，请在 {retry_after} 秒后重试"
    raise HTTPException(status_code=429, detail=detail)
