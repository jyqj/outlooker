from __future__ import annotations

import asyncio
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from fastapi import HTTPException

from ..config import DEFAULT_EMAIL_LIMIT, INBOX_FOLDER_NAME, logger
from ..database import db_manager
from ..imap_client import IMAPEmailClient
from ..messages import ERROR_EMAIL_NOT_CONFIGURED, ERROR_EMAIL_NOT_PROVIDED
from ..security import decrypt_if_needed
from .account_utils import _load_accounts_from_files, _normalize_email
from .constants import MAX_EMAIL_LIMIT, MIN_EMAIL_LIMIT


class EmailManager:
    """统一封装邮件获取逻辑和账户缓存"""

    def __init__(self) -> None:
        self._accounts_cache: Optional[Dict[str, Dict[str, str]]] = None
        self._accounts_lock: Optional[asyncio.Lock] = None
        self._accounts_lock_loop: Optional[asyncio.AbstractEventLoop] = None
        self._clients: Dict[str, IMAPEmailClient] = {}
        self._client_tokens: Dict[str, str] = {}
        self._clients_lock: Optional[asyncio.Lock] = None
        self._clients_lock_loop: Optional[asyncio.AbstractEventLoop] = None
        self._accounts_source: str = "unknown"
        self._metrics = {
            "cache_hits": 0,
            "cache_misses": 0,
            "client_reuses": 0,
            "client_creates": 0,
            "db_loads": 0,
            "cache_refreshes": 0,
            "last_cache_refresh_at": None,
        }

    def _get_accounts_lock(self) -> asyncio.Lock:
        current_loop = asyncio.get_running_loop()
        if self._accounts_lock is None or self._accounts_lock_loop is not current_loop:
            self._accounts_lock = asyncio.Lock()
            self._accounts_lock_loop = current_loop
        return self._accounts_lock

    def _get_clients_lock(self) -> asyncio.Lock:
        current_loop = asyncio.get_running_loop()
        if self._clients_lock is None or self._clients_lock_loop is not current_loop:
            self._clients_lock = asyncio.Lock()
            self._clients_lock_loop = current_loop
        return self._clients_lock

    async def load_accounts(self, force_refresh: bool = False) -> Dict[str, Dict[str, str]]:
        if not force_refresh and self._accounts_cache is not None:
            self._metrics["cache_hits"] += 1
            return dict(self._accounts_cache)

        async with self._get_accounts_lock():
            if not force_refresh and self._accounts_cache is not None:
                self._metrics["cache_hits"] += 1
                return dict(self._accounts_cache)

            self._metrics["cache_misses"] += 1
            self._metrics["db_loads"] += 1
            accounts = await db_manager.get_all_accounts()

            if accounts:
                self._accounts_source = "database"
                # 解密数据库中的敏感字段
                for email, info in accounts.items():
                    if info.get("password"):
                        info["password"] = decrypt_if_needed(info["password"])
                    if info.get("refresh_token"):
                        info["refresh_token"] = decrypt_if_needed(info["refresh_token"])
            else:
                logger.warning("数据库为空，从配置文件加载账户（仅用于初始化）")
                accounts = _load_accounts_from_files()
                self._accounts_source = "file" if accounts else "none"

            self._accounts_cache = accounts
            self._metrics["cache_refreshes"] += 1
            self._metrics["last_cache_refresh_at"] = datetime.utcnow().isoformat()
            return dict(accounts)

    async def invalidate_accounts_cache(self) -> None:
        async with self._get_accounts_lock():
            self._accounts_cache = None

    async def _get_account_info(self, email: str) -> Tuple[str, Dict[str, str]]:
        accounts = await self.load_accounts()
        lookup = {addr.lower(): addr for addr in accounts.keys()}
        normalized = _normalize_email(email)
        actual_email = lookup.get(normalized)

        if not actual_email:
            raise HTTPException(status_code=404, detail=ERROR_EMAIL_NOT_CONFIGURED)

        return actual_email, accounts[actual_email]

    async def _get_or_create_client(self, email: str, account_info: Dict[str, str]) -> IMAPEmailClient:
        """复用或创建 IMAP 客户端"""

        async with self._get_clients_lock():
            refresh_token = account_info.get("refresh_token", "")
            client = self._clients.get(email)

            if client and self._client_tokens.get(email) == refresh_token:
                self._metrics["client_reuses"] += 1
                return client

            if client:
                try:
                    await client.cleanup()
                except Exception as exc:
                    logger.warning(f"释放IMAP客户端失败({email}): {exc}")

            new_client = IMAPEmailClient(email, account_info)
            self._clients[email] = new_client
            self._client_tokens[email] = refresh_token
            self._metrics["client_creates"] += 1
            return new_client

    async def get_messages(
        self, email: str, top: Optional[int] = None, folder: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        if not email or not email.strip():
            raise HTTPException(status_code=400, detail=ERROR_EMAIL_NOT_PROVIDED)

        actual_email, account_info = await self._get_account_info(email)
        client = await self._get_or_create_client(actual_email, account_info)
        limit = self._normalize_limit(top)

        folder_id = folder or INBOX_FOLDER_NAME
        logger.info(f"开始获取 {actual_email} ({folder_id}) 的最新 {limit} 封邮件")
        return await client.get_messages_with_content(folder_id=folder_id, top=limit)

    async def cleanup_all(self) -> None:
        async with self._get_clients_lock():
            clients = list(self._clients.values())
            self._clients.clear()
            self._client_tokens.clear()

        for client in clients:
            try:
                await client.cleanup()
            except Exception as exc:
                logger.warning(f"清理IMAP客户端失败: {exc}")

    async def get_metrics(self) -> Dict[str, Any]:
        """返回当前性能指标快照并落盘"""
        hits = self._metrics.get("cache_hits", 0)
        misses = self._metrics.get("cache_misses", 0)
        total = hits + misses
        hit_rate = round(hits / total, 3) if total else None

        snapshot = {
            **self._metrics,
            "accounts_source": self._accounts_source,
            "accounts_count": len(self._accounts_cache or {}),
            "cache_hit_rate": hit_rate,
        }

        cache_stats = await db_manager.get_email_cache_stats()
        snapshot["email_cache"] = cache_stats

        await db_manager.upsert_system_metric("email_manager", snapshot)
        return snapshot

    @staticmethod
    def _normalize_limit(top: Optional[int]) -> int:
        if top is None:
            value = DEFAULT_EMAIL_LIMIT
        else:
            try:
                value = int(top)
            except (TypeError, ValueError):
                value = DEFAULT_EMAIL_LIMIT

        return max(MIN_EMAIL_LIMIT, min(MAX_EMAIL_LIMIT, value))


email_manager = EmailManager()


async def load_accounts_config(force_refresh: bool = False) -> Dict[str, Dict[str, str]]:
    """提供给路由的账户加载入口"""
    return await email_manager.load_accounts(force_refresh=force_refresh)
