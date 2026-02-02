#!/usr/bin/env python3
"""
Account cache management service.
"""
from __future__ import annotations

import asyncio
import copy
import logging
from datetime import datetime, timezone
from typing import Any

from ..auth.security import decrypt_if_needed
from ..db import db_manager
from .account_utils import _load_accounts_from_files

logger = logging.getLogger(__name__)


class AccountCacheService:
    """账户缓存管理服务"""

    def __init__(self) -> None:
        self._cache: dict[str, dict[str, str]] | None = None
        self._lock: asyncio.Lock | None = None
        self._lock_loop: asyncio.AbstractEventLoop | None = None
        self._source: str = "unknown"
        self._metrics: dict[str, Any] = {
            "cache_hits": 0,
            "cache_misses": 0,
            "db_loads": 0,
            "cache_refreshes": 0,
            "last_refresh_at": None,
        }

    def _get_lock(self) -> asyncio.Lock:
        current_loop = asyncio.get_running_loop()
        if self._lock is None or self._lock_loop is not current_loop:
            self._lock = asyncio.Lock()
            self._lock_loop = current_loop
        return self._lock

    async def load(self, force_refresh: bool = False) -> dict[str, dict[str, str]]:
        """加载账户数据（带缓存）"""
        if not force_refresh and self._cache is not None:
            self._metrics["cache_hits"] += 1
            return copy.deepcopy(self._cache)

        async with self._get_lock():
            if not force_refresh and self._cache is not None:
                self._metrics["cache_hits"] += 1
                return copy.deepcopy(self._cache)

            self._metrics["cache_misses"] += 1
            self._metrics["db_loads"] += 1

            accounts = await db_manager.get_all_accounts()

            if accounts:
                self._source = "database"
                # 解密敏感字段
                for email, info in accounts.items():
                    if info.get("password"):
                        info["password"] = decrypt_if_needed(info["password"])
                    if info.get("refresh_token"):
                        info["refresh_token"] = decrypt_if_needed(info["refresh_token"])
            else:
                logger.warning("数据库为空，从配置文件加载账户")
                accounts = _load_accounts_from_files()
                self._source = "file" if accounts else "none"

            self._cache = accounts
            self._metrics["cache_refreshes"] += 1
            self._metrics["last_refresh_at"] = datetime.now(timezone.utc).isoformat()

            return copy.deepcopy(accounts)

    async def invalidate(self) -> None:
        """清除缓存"""
        async with self._get_lock():
            self._cache = None

    async def get_account(self, email: str) -> dict[str, str] | None:
        """获取单个账户信息"""
        accounts = await self.load()
        lookup = {addr.lower(): addr for addr in accounts.keys()}
        normalized = email.strip().lower()
        actual_email = lookup.get(normalized)

        if actual_email:
            return accounts[actual_email]
        return None

    def get_metrics(self) -> dict[str, Any]:
        """获取缓存指标"""
        hits = self._metrics["cache_hits"]
        misses = self._metrics["cache_misses"]
        total = hits + misses

        return {
            **self._metrics,
            "source": self._source,
            "cached_count": len(self._cache or {}),
            "hit_rate": round(hits / total, 3) if total else None,
        }


# 全局单例
account_cache = AccountCacheService()
