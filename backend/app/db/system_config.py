#!/usr/bin/env python3
"""
System configuration and metrics module.

Handles all system configuration related database operations including:
- System configuration key-value storage
- System metrics tracking
"""

import json
import logging
import sqlite3
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

from .base import RunInThreadMixin


class SystemConfigMixin(RunInThreadMixin):
    """Mixin providing system configuration database operations."""

    async def get_system_config(self, key: str, default_value: str | None = None) -> str | None:
        """Get a system configuration value."""

        def _sync_get(conn: sqlite3.Connection) -> str | None:
            cursor = conn.cursor()
            cursor.execute("SELECT value FROM system_config WHERE key = ?", (key,))
            row = cursor.fetchone()
            return row["value"] if row else default_value

        return await self._run_in_thread(_sync_get)

    async def set_system_config(self, key: str, value: str) -> bool:
        """Set a system configuration value."""

        def _sync_set(conn: sqlite3.Connection) -> bool:
            try:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    INSERT OR REPLACE INTO system_config (key, value, updated_at)
                    VALUES (?, ?, CURRENT_TIMESTAMP)
                    """,
                    (key, value),
                )
                conn.commit()
                return True
            except Exception as e:
                logger.error(f"设置系统配置失败: {e}")
                return False

        return await self._run_in_thread(_sync_set)

    async def upsert_system_metric(self, key: str, value: Any) -> bool:
        """Write or update a system metric."""

        def _sync_upsert(conn: sqlite3.Connection) -> bool:
            try:
                cursor = conn.cursor()

                if isinstance(value, (dict, list)):
                    payload = json.dumps(value, ensure_ascii=False)
                else:
                    payload = str(value)

                cursor.execute(
                    """
                    INSERT INTO system_metrics (key, value, updated_at)
                    VALUES (?, ?, CURRENT_TIMESTAMP)
                    ON CONFLICT(key) DO UPDATE SET
                        value=excluded.value,
                        updated_at=CURRENT_TIMESTAMP
                    """,
                    (key, payload),
                )
                conn.commit()
                return True
            except Exception as e:
                logger.error(f"写入系统指标失败: {e}")
                return False

        return await self._run_in_thread(_sync_upsert)

    async def get_all_system_metrics(self) -> dict[str, dict[str, str]]:
        """Get all system metrics."""

        def _sync_get(conn: sqlite3.Connection) -> dict[str, dict[str, str]]:
            cursor = conn.cursor()
            cursor.execute("SELECT key, value, updated_at FROM system_metrics")
            rows = cursor.fetchall()
            return {
                row["key"]: {
                    "value": row["value"],
                    "updated_at": row["updated_at"],
                }
                for row in rows
            }

        return await self._run_in_thread(_sync_get)

    async def backup_database(self, dest_path: str) -> bool:
        """Create a cold backup of the database."""

        def _sync_backup(conn: sqlite3.Connection) -> bool:
            try:
                dest = Path(dest_path)
                dest.parent.mkdir(parents=True, exist_ok=True)
                with sqlite3.connect(dest) as target:
                    conn.backup(target)
                return True
            except Exception as exc:
                logger.error("数据库备份失败: %s", exc)
                return False

        return await self._run_in_thread(lambda conn: _sync_backup(conn))

    async def check_database_connection(self) -> bool:
        """Check if database connection is healthy."""

        def _sync_check(conn: sqlite3.Connection) -> bool:
            try:
                cursor = conn.cursor()
                cursor.execute("SELECT 1")
                return True
            except Exception:
                return False

        return await self._run_in_thread(_sync_check)
