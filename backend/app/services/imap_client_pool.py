#!/usr/bin/env python3
"""
IMAP client connection pool.
"""
from __future__ import annotations

import asyncio
import logging
from collections import OrderedDict
from typing import Any

from ..imap_client import IMAPEmailClient

logger = logging.getLogger(__name__)


class IMAPClientPool:
    """IMAP 客户端连接池（LRU 淘汰策略）"""

    def __init__(self, max_clients: int | None = None) -> None:
        self._clients: OrderedDict[str, IMAPEmailClient] = OrderedDict()
        self._client_tokens: dict[str, str] = {}
        self._lock: asyncio.Lock | None = None
        self._lock_loop: asyncio.AbstractEventLoop | None = None
        self._max_clients_override = max_clients
        self._metrics: dict[str, Any] = {
            "client_reuses": 0,
            "client_creates": 0,
            "client_cleanups": 0,
        }

    @property
    def _max_clients(self) -> int:
        """延迟获取 max_clients，避免循环导入"""
        if self._max_clients_override is not None:
            return self._max_clients_override
        # 延迟导入避免循环依赖
        from ..settings import get_settings
        return get_settings().imap_pool_max_clients

    def _get_lock(self) -> asyncio.Lock:
        current_loop = asyncio.get_running_loop()
        if self._lock is None or self._lock_loop is not current_loop:
            self._lock = asyncio.Lock()
            self._lock_loop = current_loop
        return self._lock

    async def get_or_create(
        self,
        email: str,
        account_info: dict[str, str],
    ) -> IMAPEmailClient:
        """获取或创建 IMAP 客户端"""
        async with self._get_lock():
            refresh_token = account_info.get("refresh_token", "")
            client = self._clients.get(email)

            # 复用现有客户端（如果 token 未变化）
            if client and self._client_tokens.get(email) == refresh_token:
                # LRU: 移动到末尾表示最近使用
                self._clients.move_to_end(email)
                self._metrics["client_reuses"] += 1
                return client

            # 清理旧客户端
            if client:
                try:
                    await client.cleanup()
                    self._metrics["client_cleanups"] += 1
                except Exception as e:
                    logger.warning(f"释放旧 IMAP 客户端失败 ({email}): {e}")

            # 如果达到最大数量，清理最早的客户端
            if len(self._clients) >= self._max_clients:
                await self._evict_oldest()

            # 创建新客户端
            new_client = IMAPEmailClient(email, account_info)
            self._clients[email] = new_client
            self._client_tokens[email] = refresh_token
            self._metrics["client_creates"] += 1

            return new_client

    async def _evict_oldest(self) -> None:
        """淘汰最久未使用的客户端（LRU）"""
        if not self._clients:
            return

        # OrderedDict 的第一个元素是最久未使用的
        oldest_email, client = self._clients.popitem(last=False)
        self._client_tokens.pop(oldest_email, None)

        try:
            await client.cleanup()
            self._metrics["client_cleanups"] += 1
        except Exception as e:
            logger.warning(f"清理淘汰客户端失败 ({oldest_email}): {e}")

    async def remove(self, email: str) -> None:
        """移除指定客户端"""
        async with self._get_lock():
            client = self._clients.pop(email, None)
            self._client_tokens.pop(email, None)

            if client:
                try:
                    await client.cleanup()
                    self._metrics["client_cleanups"] += 1
                except Exception as e:
                    logger.warning(f"清理客户端失败 ({email}): {e}")

    async def cleanup_all(self) -> None:
        """清理所有客户端"""
        async with self._get_lock():
            clients = list(self._clients.values())
            self._clients.clear()
            self._client_tokens.clear()

        for client in clients:
            try:
                await client.cleanup()
                self._metrics["client_cleanups"] += 1
            except Exception as e:
                logger.warning(f"清理客户端失败: {e}")

    def get_metrics(self) -> dict[str, Any]:
        """获取连接池指标"""
        return {
            **self._metrics,
            "active_clients": len(self._clients),
            "max_clients": self._max_clients,
        }


# 全局单例
imap_pool = IMAPClientPool()
