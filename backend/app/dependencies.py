from __future__ import annotations

from functools import lru_cache
from typing import TYPE_CHECKING, Annotated

from fastapi import Depends, Header, HTTPException, Request

from .core.rate_limiter import public_api_rate_limiter
from .settings import get_settings
from .utils.request_utils import get_client_ip

if TYPE_CHECKING:
    from .db.manager import DatabaseManager
    from .services.email_service import EmailManager
    from .services.imap_client_pool import IMAPClientPool
    from .services.account_cache_service import AccountCacheService

settings = get_settings()


# ============================================================================
# 服务依赖注入
# ============================================================================
# 使用 FastAPI 的 Depends 机制实现依赖注入
# 便于测试时替换服务实例


@lru_cache
def get_db_manager() -> "DatabaseManager":
    """获取数据库管理器实例
    
    使用 lru_cache 确保单例模式，同时支持测试时清除缓存替换实例。
    """
    from .services import db_manager
    return db_manager


@lru_cache
def get_email_manager() -> "EmailManager":
    """获取邮件管理器实例"""
    from .services import email_manager
    return email_manager


@lru_cache
def get_imap_pool() -> "IMAPClientPool":
    """获取 IMAP 连接池实例"""
    from .services import imap_pool
    return imap_pool


@lru_cache
def get_account_cache() -> "AccountCacheService":
    """获取账户缓存服务实例"""
    from .services import account_cache
    return account_cache


# 类型别名，用于路由函数参数
DbManager = Annotated["DatabaseManager", Depends(get_db_manager)]
EmailMgr = Annotated["EmailManager", Depends(get_email_manager)]
ImapPool = Annotated["IMAPClientPool", Depends(get_imap_pool)]
AccountCache = Annotated["AccountCacheService", Depends(get_account_cache)]


def clear_service_caches() -> None:
    """清除所有服务缓存（用于测试）"""
    get_db_manager.cache_clear()
    get_email_manager.cache_clear()
    get_imap_pool.cache_clear()
    get_account_cache.cache_clear()


async def verify_public_token(x_public_token: str | None = Header(None)) -> None:
    """校验公共接口调用口令（X-Public-Token）。"""
    if not x_public_token or x_public_token != settings.public_api_token:
        raise HTTPException(status_code=401, detail="未授权的公共接口访问")


# ============================================================================
# 管理员认证依赖
# ============================================================================


async def get_admin_user(
    authorization: Annotated[str | None, Header()] = None
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
    from .auth.jwt import get_current_admin
    return get_current_admin(authorization)


# 类型别名，用于路由函数参数
AdminUser = Annotated[str, Depends(get_admin_user)]


async def enforce_public_rate_limit(request: Request, email: str | None = None) -> None:
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
