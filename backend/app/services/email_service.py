#!/usr/bin/env python3
"""
Email service - Facade for email operations.

This module provides a unified interface for email operations by delegating
to specialized services:
- AccountCacheService: Account data caching
- IMAPClientPool: IMAP client connection pooling
- EmailFetchService: Email fetching with caching
"""
from __future__ import annotations

import logging
from typing import Any

from ..db import db_manager
from .account_cache_service import AccountCacheService, account_cache
from .email_fetch_service import EmailFetchService, email_fetch_service
from .imap_client_pool import IMAPClientPool, imap_pool

logger = logging.getLogger(__name__)


class EmailManager:
    """统一封装邮件获取逻辑（门面模式）

    此类作为向后兼容的入口点，内部委托给各个专用服务：
    - account_cache: 账户缓存管理
    - imap_pool: IMAP 客户端连接池
    - email_fetch_service: 邮件获取服务
    """

    def __init__(self) -> None:
        # 保持向后兼容 - 使用全局单例
        self._account_cache = account_cache
        self._imap_pool = imap_pool
        self._email_fetch_service = email_fetch_service

    async def load_accounts(self, force_refresh: bool = False) -> dict[str, dict[str, str]]:
        """加载账户数据（带缓存）

        Args:
            force_refresh: 是否强制刷新缓存

        Returns:
            账户字典，键为邮箱地址，值为账户信息
        """
        return await self._account_cache.load(force_refresh)

    async def invalidate_accounts_cache(self) -> None:
        """清除账户缓存"""
        await self._account_cache.invalidate()

    async def get_messages(
        self,
        email: str,
        top: int | None = None,
        folder: str | None = None,
        force_refresh: bool = False,
    ) -> list[dict[str, Any]]:
        """获取邮件消息

        Args:
            email: 邮箱地址
            top: 最大返回数量
            folder: 邮件文件夹
            force_refresh: 是否强制刷新

        Returns:
            邮件消息列表
        """
        return await self._email_fetch_service.get_messages(
            email, top, folder, force_refresh
        )

    async def cleanup_all(self) -> None:
        """清理所有 IMAP 客户端连接"""
        return await self._imap_pool.cleanup_all()

    async def get_metrics(self) -> dict[str, Any]:
        """返回当前性能指标快照并落盘

        合并各服务的指标，提供统一的监控视图。

        Returns:
            包含所有服务指标的字典
        """
        # 获取各服务的指标
        cache_metrics = self._account_cache.get_metrics()
        pool_metrics = self._imap_pool.get_metrics()

        # 合并指标（保持向后兼容的字段名）
        snapshot: dict[str, Any] = {
            # 账户缓存指标
            "cache_hits": cache_metrics.get("cache_hits", 0),
            "cache_misses": cache_metrics.get("cache_misses", 0),
            "db_loads": cache_metrics.get("db_loads", 0),
            "cache_refreshes": cache_metrics.get("cache_refreshes", 0),
            "last_cache_refresh_at": cache_metrics.get("last_refresh_at"),
            "accounts_source": cache_metrics.get("source", "unknown"),
            "accounts_count": cache_metrics.get("cached_count", 0),
            # IMAP 连接池指标
            "client_reuses": pool_metrics.get("client_reuses", 0),
            "client_creates": pool_metrics.get("client_creates", 0),
            "client_cleanups": pool_metrics.get("client_cleanups", 0),
            "active_clients": pool_metrics.get("active_clients", 0),
            "max_clients": pool_metrics.get("max_clients", 100),
        }

        # 计算缓存命中率
        hits = snapshot["cache_hits"]
        misses = snapshot["cache_misses"]
        total = hits + misses
        snapshot["cache_hit_rate"] = round(hits / total, 3) if total else None

        # 获取邮件缓存统计
        cache_stats = await db_manager.get_email_cache_stats()
        snapshot["email_cache"] = cache_stats

        # 落盘指标
        await db_manager.upsert_system_metric("email_manager", snapshot)
        return snapshot

    def is_ready(self) -> bool:
        """Check if the email manager is ready to handle requests.

        Returns:
            True if ready, False otherwise
        """
        # Email manager is always ready once initialized
        # In the future, we could add more checks like:
        # - IMAP server connectivity
        # - Account configuration validity
        return True


# 全局单例
email_manager = EmailManager()


async def load_accounts_config(force_refresh: bool = False) -> dict[str, dict[str, str]]:
    """提供给路由的账户加载入口

    Args:
        force_refresh: 是否强制刷新缓存

    Returns:
        账户字典
    """
    return await email_manager.load_accounts(force_refresh=force_refresh)


# 导出专用服务供直接使用
__all__ = [
    "EmailManager",
    "email_manager",
    "load_accounts_config",
    # 专用服务
    "AccountCacheService",
    "account_cache",
    "IMAPClientPool",
    "imap_pool",
    "EmailFetchService",
    "email_fetch_service",
]
