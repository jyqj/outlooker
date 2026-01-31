#!/usr/bin/env python3
"""
Audit and rate limiting module.

Handles login audit logging and rate limiting related database operations:
- Login attempt recording
- Failure counting
- Account lockout management
"""

import logging
import sqlite3
from datetime import datetime

logger = logging.getLogger(__name__)

from .base import RunInThreadMixin


class AuditMixin(RunInThreadMixin):
    """Mixin providing audit and rate limiting database operations."""

    async def record_login_attempt(
        self, ip: str, username: str, success: bool, reason: str = ""
    ) -> None:
        """Record a login attempt."""

        def _sync_record(conn: sqlite3.Connection) -> None:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO admin_login_attempts (ip, username, success, reason)
                VALUES (?, ?, ?, ?)
                """,
                (ip, username, 1 if success else 0, reason),
            )
            conn.commit()

        await self._run_in_thread(_sync_record)

    async def count_recent_failures(
        self, ip: str, username: str, window_seconds: int
    ) -> int:
        """Count recent login failures within a time window."""

        def _sync_count(conn: sqlite3.Connection) -> int:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT COUNT(*) FROM admin_login_attempts
                WHERE ip = ? AND username = ? AND success = 0
                  AND created_at > datetime('now', ?)
                  AND id > COALESCE(
                    (
                      SELECT MAX(id) FROM admin_login_attempts
                      WHERE ip = ? AND username = ? AND success = 1
                    ),
                    0
                  )
                """,
                (ip, username, f"-{window_seconds} seconds", ip, username),
            )
            row = cursor.fetchone()
            return row[0] if row else 0

        return await self._run_in_thread(_sync_count)

    async def set_lockout(
        self, ip: str, username: str, lockout_until: datetime
    ) -> None:
        """Set account lockout."""

        def _sync_set(conn: sqlite3.Connection) -> None:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO admin_lockouts (ip, username, lockout_until)
                VALUES (?, ?, ?)
                ON CONFLICT(ip, username) DO UPDATE SET lockout_until=excluded.lockout_until
                """,
                (ip, username, lockout_until.isoformat()),
            )
            conn.commit()

        await self._run_in_thread(_sync_set)

    async def get_lockout(self, ip: str, username: str) -> datetime | None:
        """
        Get lockout expiration time.
        
        Automatically clears expired lockouts.
        """

        def _sync_get(conn: sqlite3.Connection) -> datetime | None:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT lockout_until FROM admin_lockouts
                WHERE ip = ? AND username = ?
                """,
                (ip, username),
            )
            row = cursor.fetchone()
            if not row:
                return None
            lockout_until = datetime.fromisoformat(row["lockout_until"])
            if lockout_until < datetime.utcnow():
                cursor.execute(
                    "DELETE FROM admin_lockouts WHERE ip = ? AND username = ?",
                    (ip, username),
                )
                conn.commit()
                return None
            return lockout_until

        return await self._run_in_thread(_sync_get)

    async def clear_lockout(self, ip: str, username: str) -> None:
        """Clear account lockout."""

        def _sync_clear(conn: sqlite3.Connection) -> None:
            cursor = conn.cursor()
            cursor.execute(
                "DELETE FROM admin_lockouts WHERE ip = ? AND username = ?",
                (ip, username),
            )
            conn.commit()

        await self._run_in_thread(_sync_clear)

    async def get_login_audit_stats(self) -> dict:
        """Get login audit statistics."""

        def _sync_stats(conn: sqlite3.Connection) -> dict:
            cursor = conn.cursor()

            # Total attempts
            cursor.execute("SELECT COUNT(*) FROM admin_login_attempts")
            total = cursor.fetchone()[0]

            # Successful logins
            cursor.execute("SELECT COUNT(*) FROM admin_login_attempts WHERE success = 1")
            successful = cursor.fetchone()[0]

            # Failed logins
            cursor.execute("SELECT COUNT(*) FROM admin_login_attempts WHERE success = 0")
            failed = cursor.fetchone()[0]

            # Active lockouts
            cursor.execute(
                """
                SELECT COUNT(*) FROM admin_lockouts 
                WHERE lockout_until > datetime('now')
                """
            )
            active_lockouts = cursor.fetchone()[0]

            # Recent failures (last 24 hours)
            cursor.execute(
                """
                SELECT COUNT(*) FROM admin_login_attempts 
                WHERE success = 0 AND created_at > datetime('now', '-1 day')
                """
            )
            recent_failures = cursor.fetchone()[0]

            return {
                "total_attempts": total,
                "successful_logins": successful,
                "failed_logins": failed,
                "active_lockouts": active_lockouts,
                "recent_failures_24h": recent_failures,
            }

        return await self._run_in_thread(_sync_stats)

    async def cleanup_old_audit_logs(self, days: int = 90) -> int:
        """Clean up old audit logs."""
        # 白名单校验：限制 days 参数范围，防止异常输入
        days = max(1, min(int(days), 365))

        def _sync_cleanup(conn: sqlite3.Connection) -> int:
            try:
                cursor = conn.cursor()
                # 使用参数化查询：先计算阈值时间，避免 f-string 拼接
                from datetime import timedelta
                threshold = (datetime.utcnow() - timedelta(days=days)).isoformat()
                cursor.execute(
                    "DELETE FROM admin_login_attempts WHERE created_at < ?",
                    (threshold,),
                )
                deleted = cursor.rowcount
                conn.commit()
                return deleted
            except Exception as e:
                logger.error(f"清理旧审计日志失败: {e}")
                return 0

        return await self._run_in_thread(_sync_cleanup)
