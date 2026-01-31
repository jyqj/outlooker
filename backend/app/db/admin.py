#!/usr/bin/env python3
"""
Admin user and refresh token management module.

Handles all admin-related database operations including:
- Admin user CRUD
- Refresh token management
- Password management
"""

import logging
import sqlite3
from datetime import datetime

logger = logging.getLogger(__name__)

from .base import RunInThreadMixin


class AdminMixin(RunInThreadMixin):
    """Mixin providing admin-related database operations."""

    async def get_admin_by_username(self, username: str) -> dict[str, str] | None:
        """Get admin by username."""

        def _sync_get(conn: sqlite3.Connection) -> dict[str, str] | None:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT id, username, password_hash, role, is_active, created_at, updated_at
                FROM admin_users
                WHERE username = ?
                """,
                (username,),
            )
            row = cursor.fetchone()
            if not row:
                return None
            return dict(row)

        return await self._run_in_thread(_sync_get)

    async def get_admin_by_id(self, admin_id: int) -> dict[str, str] | None:
        """Get admin by ID."""

        def _sync_get(conn: sqlite3.Connection) -> dict[str, str] | None:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT id, username, password_hash, role, is_active, created_at, updated_at
                FROM admin_users
                WHERE id = ?
                """,
                (admin_id,),
            )
            row = cursor.fetchone()
            if not row:
                return None
            return dict(row)

        return await self._run_in_thread(_sync_get)

    async def create_admin_user(
        self,
        username: str,
        password_hash: str,
        role: str = "admin",
        is_active: bool = True,
    ) -> int | None:
        """Create a new admin user."""

        def _sync_create(conn: sqlite3.Connection) -> int | None:
            cursor = conn.cursor()
            try:
                cursor.execute(
                    """
                    INSERT INTO admin_users (username, password_hash, role, is_active)
                    VALUES (?, ?, ?, ?)
                    """,
                    (username, password_hash, role, 1 if is_active else 0),
                )
                conn.commit()
                return cursor.lastrowid
            except sqlite3.IntegrityError:
                return None

        return await self._run_in_thread(_sync_create)

    async def update_admin_password(self, admin_id: int, password_hash: str) -> bool:
        """Update admin password."""

        def _sync_update(conn: sqlite3.Connection) -> bool:
            cursor = conn.cursor()
            cursor.execute(
                """
                UPDATE admin_users
                SET password_hash = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                (password_hash, admin_id),
            )
            conn.commit()
            return cursor.rowcount > 0

        return await self._run_in_thread(_sync_update)

    async def count_admin_users(self) -> int:
        """Count total admin users."""

        def _sync_count(conn: sqlite3.Connection) -> int:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM admin_users")
            row = cursor.fetchone()
            return row[0] if row else 0

        return await self._run_in_thread(_sync_count)

    async def insert_admin_refresh_token(
        self,
        token_id: str,
        admin_id: int,
        token_hash: str,
        expires_at: datetime,
        user_agent: str | None,
        ip_address: str | None,
    ) -> bool:
        """Save an admin refresh token."""

        def _sync_insert(conn: sqlite3.Connection) -> bool:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO admin_refresh_tokens
                (token_id, admin_id, token_hash, user_agent, ip_address, expires_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    token_id,
                    admin_id,
                    token_hash,
                    user_agent,
                    ip_address,
                    expires_at.isoformat(),
                ),
            )
            conn.commit()
            return True

        return await self._run_in_thread(_sync_insert)

    async def get_admin_refresh_token(self, token_id: str) -> dict[str, str] | None:
        """Get a refresh token."""

        def _sync_get(conn: sqlite3.Connection) -> dict[str, str] | None:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT token_id, admin_id, token_hash, user_agent, ip_address, expires_at, revoked_at
                FROM admin_refresh_tokens
                WHERE token_id = ?
                """,
                (token_id,),
            )
            row = cursor.fetchone()
            if not row:
                return None
            return dict(row)

        return await self._run_in_thread(_sync_get)

    async def revoke_admin_refresh_token(self, token_id: str, reason: str = "") -> bool:
        """Revoke a refresh token."""

        def _sync_revoke(conn: sqlite3.Connection) -> bool:
            cursor = conn.cursor()
            cursor.execute(
                """
                UPDATE admin_refresh_tokens
                SET revoked_at = CURRENT_TIMESTAMP
                WHERE token_id = ? AND revoked_at IS NULL
                """,
                (token_id,),
            )
            conn.commit()
            return cursor.rowcount > 0

        success = await self._run_in_thread(_sync_revoke)
        if not success:
            logger.warning("撤销刷新令牌失败或已撤销: %s", token_id)
        return success

    async def cleanup_expired_refresh_tokens(self) -> int:
        """Clean up expired or revoked refresh tokens."""

        def _sync_cleanup(conn: sqlite3.Connection) -> int:
            cursor = conn.cursor()
            cursor.execute(
                """
                DELETE FROM admin_refresh_tokens
                WHERE expires_at < datetime('now', '-1 day') OR revoked_at IS NOT NULL
                """
            )
            deleted = cursor.rowcount
            conn.commit()
            return deleted

        return await self._run_in_thread(_sync_cleanup)
