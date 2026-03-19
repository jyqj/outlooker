#!/usr/bin/env python3
"""
Outlook account asset database operations.

此 mixin 先提供 T009 所需的最小能力：
- 创建 Outlook 资产
- 查询单个 Outlook 资产
- 更新单个 Outlook 资产
"""

from __future__ import annotations

import sqlite3
import json
from typing import Any

from .base import RunInThreadMixin


class OutlookAccountsMixin(RunInThreadMixin):
    """Mixin providing minimal Outlook account asset operations."""

    async def create_outlook_account(
        self,
        email: str,
        status: str = "active",
        account_type: str = "consumer",
        source_account_email: str | None = None,
        default_channel_id: int | None = None,
        notes: str = "",
    ) -> bool:
        def _sync_create(conn: sqlite3.Connection) -> bool:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO outlook_accounts (
                    email, status, account_type, source_account_email, default_channel_id, notes
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    email,
                    status,
                    account_type,
                    source_account_email,
                    default_channel_id,
                    notes,
                ),
            )
            conn.commit()
            return True

        return await self._run_in_thread(_sync_create)

    async def get_outlook_account(self, email: str) -> dict[str, Any] | None:
        def _sync_get(conn: sqlite3.Connection) -> dict[str, Any] | None:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT
                    email,
                    status,
                    account_type,
                    source_account_email,
                    default_channel_id,
                    notes,
                    last_synced_at,
                    created_at,
                    updated_at
                FROM outlook_accounts
                WHERE email = ?
                """,
                (email,),
            )
            row = cursor.fetchone()
            return dict(row) if row else None

        return await self._run_in_thread(_sync_get)

    async def get_outlook_account_by_source_email(
        self, source_account_email: str
    ) -> dict[str, Any] | None:
        def _sync_get(conn: sqlite3.Connection) -> dict[str, Any] | None:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT
                    email,
                    status,
                    account_type,
                    source_account_email,
                    default_channel_id,
                    notes,
                    last_synced_at,
                    created_at,
                    updated_at
                FROM outlook_accounts
                WHERE source_account_email = ?
                ORDER BY created_at DESC
                LIMIT 1
                """,
                (source_account_email,),
            )
            row = cursor.fetchone()
            return dict(row) if row else None

        return await self._run_in_thread(_sync_get)

    async def update_outlook_account(self, email: str, **fields: Any) -> bool:
        allowed_fields = {
            "status",
            "account_type",
            "source_account_email",
            "default_channel_id",
            "notes",
            "last_synced_at",
        }
        updates = {key: value for key, value in fields.items() if key in allowed_fields}
        if not updates:
            return False

        def _sync_update(conn: sqlite3.Connection) -> bool:
            cursor = conn.cursor()
            assignments = ", ".join(f"{key} = ?" for key in updates)
            values = list(updates.values())
            values.extend([email])
            cursor.execute(
                f"""
                UPDATE outlook_accounts
                SET {assignments}, updated_at = CURRENT_TIMESTAMP
                WHERE email = ?
                """,
                values,
            )
            conn.commit()
            return cursor.rowcount > 0

        return await self._run_in_thread(_sync_update)

    async def upsert_account_capabilities(
        self,
        email: str,
        imap_ready: bool = False,
        graph_ready: bool = False,
        protocol_ready: bool = False,
        browser_fallback_ready: bool = False,
    ) -> bool:
        def _sync_upsert(conn: sqlite3.Connection) -> bool:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO account_capabilities (
                    email, imap_ready, graph_ready, protocol_ready, browser_fallback_ready
                ) VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(email) DO UPDATE SET
                    imap_ready = excluded.imap_ready,
                    graph_ready = excluded.graph_ready,
                    protocol_ready = excluded.protocol_ready,
                    browser_fallback_ready = excluded.browser_fallback_ready,
                    updated_at = CURRENT_TIMESTAMP
                """,
                (
                    email,
                    1 if imap_ready else 0,
                    1 if graph_ready else 0,
                    1 if protocol_ready else 0,
                    1 if browser_fallback_ready else 0,
                ),
            )
            conn.commit()
            return True

        return await self._run_in_thread(_sync_upsert)

    async def get_account_capabilities(self, email: str) -> dict[str, Any] | None:
        def _sync_get(conn: sqlite3.Connection) -> dict[str, Any] | None:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT
                    email,
                    imap_ready,
                    graph_ready,
                    protocol_ready,
                    browser_fallback_ready,
                    updated_at
                FROM account_capabilities
                WHERE email = ?
                """,
                (email,),
            )
            row = cursor.fetchone()
            return dict(row) if row else None

        return await self._run_in_thread(_sync_get)

    async def upsert_account_profile_cache(
        self,
        email: str,
        profile: dict[str, Any] | str,
        synced_at: str | None = None,
    ) -> bool:
        profile_json = profile if isinstance(profile, str) else json.dumps(profile, ensure_ascii=False)

        def _sync_upsert(conn: sqlite3.Connection) -> bool:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO account_profiles_cache (email, profile_json, synced_at)
                VALUES (?, ?, COALESCE(?, CURRENT_TIMESTAMP))
                ON CONFLICT(email) DO UPDATE SET
                    profile_json = excluded.profile_json,
                    synced_at = excluded.synced_at,
                    updated_at = CURRENT_TIMESTAMP
                """,
                (email, profile_json, synced_at),
            )
            conn.commit()
            return True

        return await self._run_in_thread(_sync_upsert)

    async def get_account_profile_cache(self, email: str) -> dict[str, Any] | None:
        def _sync_get(conn: sqlite3.Connection) -> dict[str, Any] | None:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT email, profile_json, synced_at, updated_at
                FROM account_profiles_cache
                WHERE email = ?
                """,
                (email,),
            )
            row = cursor.fetchone()
            return dict(row) if row else None

        return await self._run_in_thread(_sync_get)

    async def list_outlook_accounts(
        self,
        status: str | None = None,
        account_type: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        def _sync_list(conn: sqlite3.Connection) -> list[dict[str, Any]]:
            cursor = conn.cursor()
            conditions: list[str] = []
            params: list[Any] = []
            if status:
                conditions.append("status = ?")
                params.append(status)
            if account_type:
                conditions.append("account_type = ?")
                params.append(account_type)

            where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""
            params.extend([max(1, limit), max(0, offset)])
            cursor.execute(
                f"""
                SELECT
                    email,
                    status,
                    account_type,
                    source_account_email,
                    default_channel_id,
                    notes,
                    last_synced_at,
                    created_at,
                    updated_at
                FROM outlook_accounts
                {where_clause}
                ORDER BY updated_at DESC, email ASC
                LIMIT ? OFFSET ?
                """,
                params,
            )
            return [dict(row) for row in cursor.fetchall()]

        return await self._run_in_thread(_sync_list)

    async def count_outlook_accounts(
        self, status: str | None = None, account_type: str | None = None
    ) -> int:
        def _sync_count(conn: sqlite3.Connection) -> int:
            cursor = conn.cursor()
            conditions: list[str] = []
            params: list[Any] = []
            if status:
                conditions.append("status = ?")
                params.append(status)
            if account_type:
                conditions.append("account_type = ?")
                params.append(account_type)

            where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""
            cursor.execute(
                f"SELECT COUNT(*) FROM outlook_accounts {where_clause}",
                params,
            )
            row = cursor.fetchone()
            return int(row[0]) if row else 0

        return await self._run_in_thread(_sync_count)

    async def upsert_account_security_method_snapshot(
        self,
        email: str,
        method_type: str,
        method_id: str,
        display_value: str = "",
        status: str = "active",
        raw_json: dict[str, Any] | str | None = None,
        synced_at: str | None = None,
    ) -> bool:
        raw_payload = raw_json if isinstance(raw_json, str) else json.dumps(raw_json or {}, ensure_ascii=False)

        def _sync_upsert(conn: sqlite3.Connection) -> bool:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO account_security_methods_snapshot (
                    email, method_type, method_id, display_value, status, raw_json, synced_at
                ) VALUES (?, ?, ?, ?, ?, ?, COALESCE(?, CURRENT_TIMESTAMP))
                ON CONFLICT(email, method_type, method_id) DO UPDATE SET
                    display_value = excluded.display_value,
                    status = excluded.status,
                    raw_json = excluded.raw_json,
                    synced_at = excluded.synced_at,
                    updated_at = CURRENT_TIMESTAMP
                """,
                (
                    email,
                    method_type,
                    method_id,
                    display_value,
                    status,
                    raw_payload,
                    synced_at,
                ),
            )
            conn.commit()
            return True

        return await self._run_in_thread(_sync_upsert)

    async def list_account_security_method_snapshots(
        self,
        email: str,
        method_type: str | None = None,
    ) -> list[dict[str, Any]]:
        def _sync_list(conn: sqlite3.Connection) -> list[dict[str, Any]]:
            cursor = conn.cursor()
            if method_type:
                cursor.execute(
                    """
                    SELECT
                        id,
                        email,
                        method_type,
                        method_id,
                        display_value,
                        status,
                        raw_json,
                        synced_at,
                        updated_at
                    FROM account_security_methods_snapshot
                    WHERE email = ? AND method_type = ?
                    ORDER BY id ASC
                    """,
                    (email, method_type),
                )
            else:
                cursor.execute(
                    """
                    SELECT
                        id,
                        email,
                        method_type,
                        method_id,
                        display_value,
                        status,
                        raw_json,
                        synced_at,
                        updated_at
                    FROM account_security_methods_snapshot
                    WHERE email = ?
                    ORDER BY method_type ASC, id ASC
                    """,
                    (email,),
                )
            return [dict(row) for row in cursor.fetchall()]

        return await self._run_in_thread(_sync_list)
