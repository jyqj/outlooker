#!/usr/bin/env python3
"""
Email cache operations module.

Handles all email caching related database operations including:
- Batched email upserts with one transaction and one retention pass
- Retrieving cached emails
- Cache statistics and cleanup
"""

import logging
import sqlite3
from typing import Any

from ..settings import get_settings
from .base import RunInThreadMixin

logger = logging.getLogger(__name__)
settings = get_settings()
INBOX_FOLDER_NAME = settings.inbox_folder_name

_EMAIL_UPSERT_SQL = """
    INSERT INTO email_cache
    (email, folder, message_id, subject, sender, received_date, body_preview, body_content, body_type)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    ON CONFLICT(email, folder, message_id)
    DO UPDATE SET
        subject = excluded.subject,
        sender = excluded.sender,
        received_date = excluded.received_date,
        body_preview = excluded.body_preview,
        body_content = excluded.body_content,
        body_type = excluded.body_type
"""


class EmailCacheMixin(RunInThreadMixin):
    """Mixin providing email cache database operations."""

    @staticmethod
    def _normalize_folder(folder: str | None) -> str:
        return (folder or INBOX_FOLDER_NAME or "INBOX").strip() or "INBOX"

    @staticmethod
    def _parse_cached_sender(sender: str) -> dict[str, dict[str, dict[str, str]]]:
        """Parse cached sender string into email address format."""
        sender = sender or ""
        if " <" in sender and "<" in sender and sender.endswith(">"):
            name = sender.split(" <")[0].strip()
            address = sender.split("<")[1].rstrip(">").strip()
        elif "<" in sender and ">" in sender:
            name = sender.split("<")[0].strip().strip('"')
            address = sender.split("<")[1].split(">")[0].strip()
        else:
            name = sender.strip() or sender
            address = sender.strip()

        payload = {"emailAddress": {"name": name, "address": address}}
        return {"sender": payload, "from": payload}

    @staticmethod
    def _serialize_message(
        email: str,
        folder_id: str,
        email_data: dict[str, Any],
    ) -> tuple[str, str, str, str, str, str, str, str, str] | None:
        """Convert an API/IMAP message into a database row."""
        message_id = str(email_data.get("id") or email_data.get("message_id") or "").strip()
        if not message_id:
            return None

        sender_container = email_data.get("sender") or email_data.get("from") or {}
        sender_info = (
            sender_container.get("emailAddress", {})
            if isinstance(sender_container, dict)
            else {}
        )
        if not isinstance(sender_info, dict):
            sender_info = {}
        sender = f"{sender_info.get('name', '')} <{sender_info.get('address', '')}>"

        body_info = email_data.get("body") or {}
        if not isinstance(body_info, dict):
            body_info = {}

        return (
            email,
            folder_id,
            message_id,
            str(email_data.get("subject") or ""),
            sender,
            str(email_data.get("receivedDateTime") or ""),
            str(email_data.get("bodyPreview") or ""),
            str(body_info.get("content") or ""),
            str(body_info.get("contentType") or "text"),
        )

    async def cache_emails(
        self,
        email: str,
        messages: list[dict[str, Any]],
        folder: str | None = None,
    ) -> int:
        """Upsert a message batch in one transaction and enforce capacity once."""
        folder_id = self._normalize_folder(folder)
        rows = [
            row
            for message in messages
            if (row := self._serialize_message(email, folder_id, message)) is not None
        ]
        if not rows:
            return 0

        cache_limit = max(0, int(settings.email_cache_limit_per_account))

        def _sync_cache_batch(conn: sqlite3.Connection) -> int:
            try:
                cursor = conn.cursor()
                cursor.executemany(_EMAIL_UPSERT_SQL, rows)

                # Run retention once per batch rather than once per message. The
                # deterministic id tie-breaker matters when a batch shares the same
                # CURRENT_TIMESTAMP value.
                cursor.execute(
                    """
                    DELETE FROM email_cache
                    WHERE email = ?
                      AND folder = ?
                      AND id NOT IN (
                          SELECT id FROM email_cache
                          WHERE email = ?
                            AND folder = ?
                          ORDER BY created_at DESC, id DESC
                          LIMIT ?
                      )
                    """,
                    (email, folder_id, email, folder_id, cache_limit),
                )

                conn.commit()
                return len(rows)
            except Exception as exc:
                conn.rollback()
                logger.error("批量缓存邮件失败: %s", exc, exc_info=True)
                return 0

        return await self._run_in_thread(_sync_cache_batch)

    async def cache_email(
        self,
        email: str,
        message_id: str,
        email_data: dict[str, Any],
        folder: str | None = None,
    ) -> bool:
        """Backward-compatible single-message facade over the batch writer."""
        payload = dict(email_data)
        payload["id"] = message_id
        return await self.cache_emails(email, [payload], folder=folder) == 1

    async def get_cached_email(
        self, email: str, message_id: str, folder: str | None = None
    ) -> dict[str, Any] | None:
        """Get a cached email by message ID."""
        folder_id = self._normalize_folder(folder)

        def _sync_get(conn: sqlite3.Connection) -> dict[str, Any] | None:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT * FROM email_cache
                WHERE email = ? AND folder = ? AND message_id = ?
                """,
                (email, folder_id, message_id),
            )
            row = cursor.fetchone()

            if row:
                sender_payload = self._parse_cached_sender(row["sender"])
                return {
                    "id": row["message_id"],
                    "subject": row["subject"],
                    "receivedDateTime": row["received_date"],
                    **sender_payload,
                    "bodyPreview": row["body_preview"],
                    "body": {
                        "content": row["body_content"],
                        "contentType": row["body_type"],
                    },
                }
            return None

        return await self._run_in_thread(_sync_get)

    async def get_cached_messages(
        self,
        email: str,
        folder: str | None = None,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        """Get cached messages for an email account in a folder (newest first)."""
        folder_id = self._normalize_folder(folder)
        limit = max(0, int(limit or 0))

        def _sync_get(conn: sqlite3.Connection) -> list[dict[str, Any]]:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT message_id, subject, sender, received_date, body_preview, body_content, body_type
                FROM email_cache
                WHERE email = ? AND folder = ?
                ORDER BY
                  CASE WHEN message_id GLOB '[0-9]*' THEN CAST(message_id AS INTEGER) ELSE 0 END DESC,
                  received_date DESC,
                  id DESC
                LIMIT ?
                """,
                (email, folder_id, limit),
            )
            rows = cursor.fetchall()
            messages: list[dict[str, Any]] = []
            for row in rows:
                sender_payload = self._parse_cached_sender(row["sender"])
                messages.append(
                    {
                        "id": row["message_id"],
                        "subject": row["subject"],
                        "receivedDateTime": row["received_date"],
                        **sender_payload,
                        "toRecipients": [],
                        "bodyPreview": row["body_preview"],
                        "body": {
                            "content": row["body_content"],
                            "contentType": row["body_type"],
                        },
                    }
                )
            return messages

        return await self._run_in_thread(_sync_get)

    async def get_email_cache_state(
        self, email: str, folder: str | None = None
    ) -> dict[str, Any]:
        """Get cache summary info for an email account's folder."""
        folder_id = self._normalize_folder(folder)

        def _sync_state(conn: sqlite3.Connection) -> dict[str, Any]:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT
                  COUNT(*) AS cached_count,
                  MAX(CASE WHEN message_id GLOB '[0-9]*' THEN CAST(message_id AS INTEGER) ELSE NULL END) AS max_uid
                FROM email_cache
                WHERE email = ? AND folder = ?
                """,
                (email, folder_id),
            )
            row = cursor.fetchone()
            cached_count = int(row["cached_count"] or 0) if row else 0
            max_uid = row["max_uid"] if row else None

            cursor.execute(
                """
                SELECT last_checked_at
                FROM email_cache_meta
                WHERE email = ? AND folder = ?
                """,
                (email, folder_id),
            )
            meta = cursor.fetchone()
            last_checked_at = meta["last_checked_at"] if meta else None

            return {
                "cached_count": cached_count,
                "last_checked_at": last_checked_at,
                "max_uid": max_uid,
            }

        return await self._run_in_thread(_sync_state)

    async def mark_email_cache_checked(
        self, email: str, folder: str | None = None
    ) -> None:
        """Record a cache check timestamp (even if no new emails)."""
        folder_id = self._normalize_folder(folder)

        def _sync_mark(conn: sqlite3.Connection) -> None:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO email_cache_meta (email, folder, last_checked_at)
                VALUES (?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(email, folder)
                DO UPDATE SET last_checked_at = CURRENT_TIMESTAMP
                """,
                (email, folder_id),
            )
            conn.commit()

        await self._run_in_thread(_sync_mark)

    async def get_email_cache_stats(self) -> dict[str, int]:
        """Get aggregate statistics for the email cache."""

        def _sync_stats(conn: sqlite3.Connection) -> dict[str, int]:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT COUNT(*) AS total_messages, COUNT(DISTINCT email) AS cached_accounts
                FROM email_cache
                """
            )
            row = cursor.fetchone()
            return {
                "total_messages": row["total_messages"] if row else 0,
                "cached_accounts": row["cached_accounts"] if row else 0,
            }

        return await self._run_in_thread(_sync_stats)

    async def reset_email_cache(self) -> None:
        """Clear all email cache data."""

        def _sync_reset(conn: sqlite3.Connection) -> None:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM email_cache")
            cursor.execute("DELETE FROM email_cache_meta")
            conn.commit()

        await self._run_in_thread(_sync_reset)

    async def cleanup_old_emails(self, days: int = 30) -> int:
        """Clean up old cached emails."""

        def _sync_cleanup(conn: sqlite3.Connection) -> int:
            try:
                cursor = conn.cursor()
                days_modifier = f"-{int(days)} days"
                cursor.execute(
                    """
                    DELETE FROM email_cache
                    WHERE created_at < datetime('now', ?)
                    """,
                    (days_modifier,),
                )
                deleted_count = cursor.rowcount
                conn.commit()
                return deleted_count
            except sqlite3.Error as exc:
                logger.error("清理旧邮件失败: %s", exc, exc_info=True)
                return 0

        return await self._run_in_thread(_sync_cleanup)

    async def delete_cached_email(
        self, email: str, message_id: str, folder: str | None = None
    ) -> bool:
        """Delete a specific cached email."""
        folder_id = self._normalize_folder(folder)

        def _sync_delete(conn: sqlite3.Connection) -> bool:
            try:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    DELETE FROM email_cache
                    WHERE email = ? AND folder = ? AND message_id = ?
                    """,
                    (email, folder_id, message_id),
                )
                conn.commit()
                return cursor.rowcount > 0
            except Exception as exc:
                logger.error("删除缓存邮件失败: %s", exc, exc_info=True)
                return False

        return await self._run_in_thread(_sync_delete)

    async def mark_email_as_read(
        self, email: str, message_id: str, folder: str | None = None
    ) -> bool:
        """
        Mark a cached email as read.

        Note: This only updates the cache. Actual IMAP marking should be done separately.
        """
        # Read status is not stored in the current cache schema.
        return True
