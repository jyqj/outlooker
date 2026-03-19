#!/usr/bin/env python3
"""
Email fetching service with caching.
"""
from __future__ import annotations

import asyncio
import logging
from datetime import UTC, datetime
from typing import Any

from ..core.exceptions import AccountNotFoundError, ValidationError
from ..core.messages import ERROR_EMAIL_NOT_PROVIDED
from ..db import db_manager
from ..settings import get_settings
from .account_cache_service import account_cache
from .account_utils import _normalize_email
from .constants import DEFAULT_EMAIL_LIMIT, MAX_EMAIL_LIMIT, MIN_EMAIL_LIMIT
from .imap_client_pool import imap_pool

logger = logging.getLogger(__name__)
_settings = get_settings()
INBOX_FOLDER_NAME = _settings.inbox_folder_name


class EmailFetchService:
    """邮件获取服务"""

    def __init__(self) -> None:
        self._refresh_locks: dict[str, asyncio.Lock] = {}
        self._refresh_locks_loop: asyncio.AbstractEventLoop | None = None
        self._account_cache = account_cache
        self._imap_pool = imap_pool
        self._db_manager = db_manager

    async def _get_or_create_client(
        self,
        email: str,
        account_info: dict[str, str],
    ):
        """Compatibility hook for tests and higher-level facades."""
        return await self._imap_pool.get_or_create(email, account_info)

    def _get_refresh_lock(self, key: str) -> asyncio.Lock:
        current_loop = asyncio.get_running_loop()
        if self._refresh_locks_loop is not current_loop:
            self._refresh_locks = {}
            self._refresh_locks_loop = current_loop

        if key not in self._refresh_locks:
            self._refresh_locks[key] = asyncio.Lock()
        return self._refresh_locks[key]

    @staticmethod
    def _is_cache_fresh(last_checked_at: str | None, ttl_seconds: int) -> bool:
        if ttl_seconds <= 0 or not last_checked_at:
            return False
        try:
            checked_at = datetime.fromisoformat(str(last_checked_at))
        except (TypeError, ValueError):
            return False
        if checked_at.tzinfo is None:
            checked_at = checked_at.replace(tzinfo=UTC)
        age_seconds = (datetime.now(UTC) - checked_at).total_seconds()
        return age_seconds <= ttl_seconds

    @staticmethod
    def _normalize_limit(top: int | None) -> int:
        if top is None:
            return DEFAULT_EMAIL_LIMIT
        try:
            value = int(top)
        except (TypeError, ValueError):
            return DEFAULT_EMAIL_LIMIT
        return max(MIN_EMAIL_LIMIT, min(MAX_EMAIL_LIMIT, value))

    def _is_cache_valid(self, metadata: dict[str, Any] | None, top: int | None = None) -> bool:
        if not metadata:
            return False
        last_refresh = metadata.get("last_refresh") or metadata.get("last_checked_at")
        email_count = metadata.get("email_count") or metadata.get("cached_count") or 0
        limit = self._normalize_limit(top)
        ttl_seconds = int(get_settings().email_cache_ttl_seconds or 0)
        return int(email_count) >= limit and self._is_cache_fresh(str(last_refresh) if last_refresh else None, ttl_seconds)

    async def _resolve_account_info(self, email: str) -> tuple[str, dict[str, str]]:
        if hasattr(self._account_cache, "get_account_info"):
            info = await self._account_cache.get_account_info(email)
            if not info:
                raise AccountNotFoundError(email)
            resolved_email = str(info.get("email") or email)
            return resolved_email, info
        return await self._get_account_info(email)

    async def _do_fetch(
        self,
        email: str,
        account_info: dict[str, str],
        top: int | None = None,
        folder: str | None = None,
    ) -> list[dict[str, Any]]:
        client = await self._get_or_create_client(email, account_info)
        limit = self._normalize_limit(top)
        if hasattr(client, "fetch_messages"):
            return await client.fetch_messages(top=limit, folder=folder)
        return await client.get_messages_with_content(folder_id=folder or INBOX_FOLDER_NAME, top=limit)

    async def fetch_emails(
        self,
        email: str,
        top: int | None = None,
        folder: str | None = None,
        force_refresh: bool = False,
    ) -> list[dict[str, Any]]:
        """Backward-compatible facade kept for legacy tests/callers."""
        actual_email, account_info = await self._resolve_account_info(email)
        metadata = None
        if hasattr(self._db_manager, "get_email_cache_metadata"):
            metadata = await self._db_manager.get_email_cache_metadata(actual_email, folder=folder)
        if not force_refresh and self._is_cache_valid(metadata, top):
            if hasattr(self._db_manager, "get_cached_emails"):
                return await self._db_manager.get_cached_emails(actual_email, folder=folder, limit=top)
        messages = await self._do_fetch(actual_email, account_info, top=top, folder=folder)
        if hasattr(self._db_manager, "save_emails_to_cache"):
            await self._db_manager.save_emails_to_cache(actual_email, messages, folder=folder)
        if hasattr(self._db_manager, "update_cache_metadata"):
            await self._db_manager.update_cache_metadata(actual_email, folder=folder, email_count=len(messages))
        return messages

    async def _get_account_info(self, email: str) -> tuple[str, dict[str, str]]:
        """获取账户信息"""
        accounts = await self._account_cache.load()
        lookup = {addr.lower(): addr for addr in accounts.keys()}
        normalized = _normalize_email(email)
        actual_email = lookup.get(normalized)

        if not actual_email:
            raise AccountNotFoundError(email)

        return actual_email, accounts[actual_email]

    async def get_messages(
        self,
        email: str,
        top: int | None = None,
        folder: str | None = None,
        force_refresh: bool = False,
    ) -> list[dict[str, Any]]:
        """获取邮件消息"""
        if not email or not email.strip():
            raise ValidationError(message=ERROR_EMAIL_NOT_PROVIDED, field="email")

        actual_email, account_info = await self._get_account_info(email)
        limit = self._normalize_limit(top)
        folder_id = folder or INBOX_FOLDER_NAME
        ttl_seconds = int(get_settings().email_cache_ttl_seconds or 0)

        # 检查缓存状态
        cache_state = await self._db_manager.get_email_cache_state(actual_email, folder=folder_id)
        cached_count = int(cache_state.get("cached_count") or 0)
        last_checked_at = cache_state.get("last_checked_at")
        is_fresh = self._is_cache_fresh(last_checked_at, ttl_seconds)

        # 缓存命中
        if not force_refresh and cached_count >= limit and is_fresh:
            logger.info("命中邮件缓存: %s (%s) limit=%s", actual_email, folder_id, limit)
            return await self._db_manager.get_cached_messages(actual_email, folder=folder_id, limit=limit)

        # 使用锁避免并发刷新
        refresh_key = f"{actual_email}:{folder_id}"
        async with self._get_refresh_lock(refresh_key):
            # 双重检查
            cache_state = await self._db_manager.get_email_cache_state(actual_email, folder=folder_id)
            cached_count = int(cache_state.get("cached_count") or 0)
            last_checked_at = cache_state.get("last_checked_at")
            is_fresh = self._is_cache_fresh(last_checked_at, ttl_seconds)

            if not force_refresh and cached_count >= limit and is_fresh:
                logger.info("命中邮件缓存(并发后): %s (%s)", actual_email, folder_id)
                return await self._db_manager.get_cached_messages(actual_email, folder=folder_id, limit=limit)

            # 获取 IMAP 客户端
            client = await self._get_or_create_client(actual_email, account_info)

            # 增量刷新 vs 全量获取
            if not force_refresh and cached_count >= limit:
                max_uid = cache_state.get("max_uid")
                if max_uid is not None:
                    logger.info(
                        "执行增量刷新: %s (%s) since_uid=%s",
                        actual_email,
                        folder_id,
                        max_uid,
                    )
                    await client.get_messages_since_uid(
                        folder_id=folder_id,
                        since_uid=int(max_uid),
                        max_count=limit,
                    )
                    await self._db_manager.mark_email_cache_checked(actual_email, folder=folder_id)
                    return await self._db_manager.get_cached_messages(
                        actual_email, folder=folder_id, limit=limit
                    )

            # 全量获取
            logger.info(
                "执行邮件拉取: %s (%s) limit=%s force=%s cached=%s",
                actual_email,
                folder_id,
                limit,
                force_refresh,
                cached_count,
            )
            messages = await client.get_messages_with_content(folder_id=folder_id, top=limit)
            await self._db_manager.mark_email_cache_checked(actual_email, folder=folder_id)
            return messages


# 全局单例
email_fetch_service = EmailFetchService()
