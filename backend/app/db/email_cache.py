#!/usr/bin/env python3
"""
Email cache operations module.

Handles all email caching related database operations including:
- Caching email messages
- Retrieving cached emails
- Cache statistics and cleanup
"""

import logging
import sqlite3
from typing import Any, Dict, List, Optional

from ..settings import get_settings
from .base import RunInThreadMixin

logger = logging.getLogger(__name__)
settings = get_settings()
INBOX_FOLDER_NAME = settings.inbox_folder_name


class EmailCacheMixin(RunInThreadMixin):
    """Mixin providing email cache database operations."""

    @staticmethod
    def _parse_cached_sender(sender: str) -> Dict[str, Dict[str, Dict[str, str]]]:
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

    async def cache_email(
        self,
        email: str,
        message_id: str,
        email_data: Dict,
        folder: Optional[str] = None,
    ) -> bool:
        """
        Cache email data with capacity control.

        Each account retains at most 100 cached emails.
        Older emails are evicted by creation time.
        """
        folder_id = (folder or INBOX_FOLDER_NAME or "INBOX").strip() or "INBOX"

        def _sync_cache(conn: sqlite3.Connection) -> bool:
            try:
                cursor = conn.cursor()

                subject = email_data.get("subject", "")
                sender_info = email_data.get("sender", {}).get("emailAddress", {})
                sender = f"{sender_info.get('name', '')} <{sender_info.get('address', '')}>"
                received_date = email_data.get("receivedDateTime", "")
                body_preview = email_data.get("bodyPreview", "")
                body_info = email_data.get("body", {})
                body_content = body_info.get("content", "")
                body_type = body_info.get("contentType", "text")

                cursor.execute(
                    """
                    INSERT OR REPLACE INTO email_cache
                    (email, folder, message_id, subject, sender, received_date, body_preview, body_content, body_type)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        email,
                        folder_id,
                        message_id,
                        subject,
                        sender,
                        received_date,
                        body_preview,
                        body_content,
                        body_type,
                    ),
                )

                # Capacity control: keep at most N cached emails per account
                cache_limit = settings.email_cache_limit_per_account
                # Use parameterized query to avoid SQL injection
                # SQLite requires a subquery wrapper for LIMIT with parameter in NOT IN
                cursor.execute(
                    """
                    DELETE FROM email_cache
                    WHERE email = ?
                      AND folder = ?
                      AND id NOT IN (
                          SELECT id FROM (
                              SELECT id FROM email_cache
                              WHERE email = ?
                                AND folder = ?
                              ORDER BY created_at DESC
                              LIMIT ?
                          )
                      )
                    """,
                    (email, folder_id, email, folder_id, cache_limit),
                )

                conn.commit()
                return True
            except Exception as e:
                logger.error(f"缓存邮件失败: {e}")
                return False

        return await self._run_in_thread(_sync_cache)

    async def get_cached_email(
        self, email: str, message_id: str, folder: Optional[str] = None
    ) -> Optional[Dict]:
        """Get a cached email by message ID."""
        folder_id = (folder or INBOX_FOLDER_NAME or "INBOX").strip() or "INBOX"

        def _sync_get(conn: sqlite3.Connection) -> Optional[Dict]:
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
                    "body": {"content": row["body_content"], "contentType": row["body_type"]},
                }
            return None

        return await self._run_in_thread(_sync_get)

    async def get_cached_messages(
        self,
        email: str,
        folder: Optional[str] = None,
        limit: int = 50,
    ) -> List[Dict]:
        """Get cached messages for an email account in a folder (newest first)."""
        folder_id = (folder or INBOX_FOLDER_NAME or "INBOX").strip() or "INBOX"
        limit = max(0, int(limit or 0))

        def _sync_get(conn: sqlite3.Connection) -> List[Dict]:
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
            messages: List[Dict] = []
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
        self, email: str, folder: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get cache summary info for an email account's folder."""
        folder_id = (folder or INBOX_FOLDER_NAME or "INBOX").strip() or "INBOX"

        def _sync_state(conn: sqlite3.Connection) -> Dict[str, Any]:
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
        self, email: str, folder: Optional[str] = None
    ) -> None:
        """Record a cache check timestamp (even if no new emails)."""
        folder_id = (folder or INBOX_FOLDER_NAME or "INBOX").strip() or "INBOX"

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

    async def get_email_cache_stats(self) -> Dict[str, int]:
        """Get aggregate statistics for the email cache."""

        def _sync_stats(conn: sqlite3.Connection) -> Dict[str, int]:
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
                # Use parameterized query - SQLite datetime modifier string is built safely
                # since days is validated as int and used in a string modifier
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
            except sqlite3.Error as e:
                logger.error(f"清理旧邮件失败: {e}", exc_info=True)
                return 0

        return await self._run_in_thread(_sync_cleanup)

    async def delete_cached_email(
        self, email: str, message_id: str, folder: Optional[str] = None
    ) -> bool:
        """Delete a specific cached email."""
        folder_id = (folder or INBOX_FOLDER_NAME or "INBOX").strip() or "INBOX"

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
            except Exception as e:
                logger.error(f"删除缓存邮件失败: {e}")
                return False

        return await self._run_in_thread(_sync_delete)

    async def mark_email_as_read(
        self, email: str, message_id: str, folder: Optional[str] = None
    ) -> bool:
        """
        Mark a cached email as read.
        
        Note: This only updates the cache. Actual IMAP marking should be done separately.
        """
        # For now, we don't track read status in cache
        # This is a placeholder for future implementation
        return True
