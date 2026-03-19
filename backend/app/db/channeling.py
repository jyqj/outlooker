#!/usr/bin/env python3
"""Channeling and auxiliary resource database operations."""

from __future__ import annotations

import sqlite3
from typing import Any

from .base import RunInThreadMixin


class ChannelingMixin(RunInThreadMixin):
    """Mixin providing minimal auxiliary resource operations."""

    async def create_aux_email_resource(
        self,
        address: str,
        provider: str = "custom",
        source_type: str = "manual",
        status: str = "available",
        channel_id: int | None = None,
        fail_count: int = 0,
        last_email_id: int | None = None,
        bound_account_email: str | None = None,
        notes: str = "",
    ) -> int:
        def _sync_create(conn: sqlite3.Connection) -> int:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO aux_email_resources (
                    address, provider, source_type, status, channel_id,
                    fail_count, last_email_id, bound_account_email, notes
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    address,
                    provider,
                    source_type,
                    status,
                    channel_id,
                    fail_count,
                    last_email_id,
                    bound_account_email,
                    notes,
                ),
            )
            conn.commit()
            return int(cursor.lastrowid)

        return await self._run_in_thread(_sync_create)

    async def get_aux_email_resource_by_address(self, address: str) -> dict[str, Any] | None:
        def _sync_get(conn: sqlite3.Connection) -> dict[str, Any] | None:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT
                    id,
                    address,
                    provider,
                    source_type,
                    status,
                    channel_id,
                    fail_count,
                    last_email_id,
                    bound_account_email,
                    notes,
                    created_at,
                    updated_at
                FROM aux_email_resources
                WHERE address = ?
                """,
                (address,),
            )
            row = cursor.fetchone()
            return dict(row) if row else None

        return await self._run_in_thread(_sync_get)

    async def get_aux_email_resource_by_id(self, resource_id: int) -> dict[str, Any] | None:
        def _sync_get(conn: sqlite3.Connection) -> dict[str, Any] | None:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT
                    id,
                    address,
                    provider,
                    source_type,
                    status,
                    channel_id,
                    fail_count,
                    last_email_id,
                    bound_account_email,
                    notes,
                    created_at,
                    updated_at
                FROM aux_email_resources
                WHERE id = ?
                """,
                (resource_id,),
            )
            row = cursor.fetchone()
            return dict(row) if row else None

        return await self._run_in_thread(_sync_get)

    async def update_aux_email_resource(self, resource_id: int, **fields: Any) -> bool:
        allowed_fields = {
            "provider",
            "source_type",
            "status",
            "channel_id",
            "fail_count",
            "last_email_id",
            "bound_account_email",
            "notes",
        }
        updates = {key: value for key, value in fields.items() if key in allowed_fields}
        if not updates:
            return False

        def _sync_update(conn: sqlite3.Connection) -> bool:
            cursor = conn.cursor()
            assignments = ", ".join(f"{key} = ?" for key in updates)
            values = list(updates.values())
            values.append(resource_id)
            cursor.execute(
                f"""
                UPDATE aux_email_resources
                SET {assignments}, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                values,
            )
            conn.commit()
            return cursor.rowcount > 0

        return await self._run_in_thread(_sync_update)

    async def create_channel(
        self,
        code: str,
        name: str,
        status: str = "active",
        priority: int = 0,
        pick_strategy: str = "round_robin",
        cooldown_seconds: int = 0,
        proxy_url: str = "",
        proxy_group: str = "",
        notes: str = "",
    ) -> int:
        def _sync_create(conn: sqlite3.Connection) -> int:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO channels (
                    code, name, status, priority, pick_strategy, cooldown_seconds, proxy_url, proxy_group, notes
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (code, name, status, priority, pick_strategy, cooldown_seconds, proxy_url, proxy_group, notes),
            )
            conn.commit()
            return int(cursor.lastrowid)

        return await self._run_in_thread(_sync_create)

    async def get_channel(self, channel_id: int) -> dict[str, Any] | None:
        def _sync_get(conn: sqlite3.Connection) -> dict[str, Any] | None:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT
                    id,
                    code,
                    name,
                    status,
                    priority,
                    pick_strategy,
                    cooldown_seconds,
                    proxy_url,
                    proxy_group,
                    notes,
                    created_at,
                    updated_at
                FROM channels
                WHERE id = ?
                """,
                (channel_id,),
            )
            row = cursor.fetchone()
            return dict(row) if row else None

        return await self._run_in_thread(_sync_get)

    async def get_channel_by_code_or_name(self, value: str) -> dict[str, Any] | None:
        def _sync_get(conn: sqlite3.Connection) -> dict[str, Any] | None:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT
                    id,
                    code,
                    name,
                    status,
                    priority,
                    pick_strategy,
                    cooldown_seconds,
                    proxy_url,
                    proxy_group,
                    notes,
                    created_at,
                    updated_at
                FROM channels
                WHERE code = ? OR name = ?
                ORDER BY priority DESC, id ASC
                LIMIT 1
                """,
                (value, value),
            )
            row = cursor.fetchone()
            return dict(row) if row else None

        return await self._run_in_thread(_sync_get)

    async def update_channel(self, channel_id: int, **fields: Any) -> bool:
        allowed_fields = {
            "code",
            "name",
            "status",
            "priority",
            "pick_strategy",
            "cooldown_seconds",
            "proxy_url",
            "proxy_group",
            "notes",
        }
        updates = {key: value for key, value in fields.items() if key in allowed_fields}
        if not updates:
            return False

        def _sync_update(conn: sqlite3.Connection) -> bool:
            cursor = conn.cursor()
            assignments = ", ".join(f"{key} = ?" for key in updates)
            values = list(updates.values())
            values.append(channel_id)
            cursor.execute(
                f"""
                UPDATE channels
                SET {assignments}, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                values,
            )
            conn.commit()
            return cursor.rowcount > 0

        return await self._run_in_thread(_sync_update)

    async def bind_account_to_channel(
        self,
        channel_id: int,
        account_email: str,
        status: str = "active",
        weight: int = 100,
        last_assigned_at: str | None = None,
    ) -> bool:
        def _sync_upsert(conn: sqlite3.Connection) -> bool:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO channel_account_relations (
                    channel_id, account_email, status, weight, last_assigned_at
                ) VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(channel_id, account_email) DO UPDATE SET
                    status = excluded.status,
                    weight = excluded.weight,
                    last_assigned_at = excluded.last_assigned_at,
                    updated_at = CURRENT_TIMESTAMP
                """,
                (channel_id, account_email, status, weight, last_assigned_at),
            )
            conn.commit()
            return True

        return await self._run_in_thread(_sync_upsert)

    async def get_channel_account_relation(
        self, channel_id: int, account_email: str
    ) -> dict[str, Any] | None:
        def _sync_get(conn: sqlite3.Connection) -> dict[str, Any] | None:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT
                    channel_id,
                    account_email,
                    status,
                    weight,
                    last_assigned_at,
                    created_at,
                    updated_at
                FROM channel_account_relations
                WHERE channel_id = ? AND account_email = ?
                """,
                (channel_id, account_email),
            )
            row = cursor.fetchone()
            return dict(row) if row else None

        return await self._run_in_thread(_sync_get)

    async def update_channel_account_relation(
        self,
        channel_id: int,
        account_email: str,
        *,
        status: str | None = None,
        weight: int | None = None,
        last_assigned_at: str | None = None,
    ) -> bool:
        updates: dict[str, Any] = {}
        if status is not None:
            updates["status"] = status
        if weight is not None:
            updates["weight"] = weight
        if last_assigned_at is not None:
            updates["last_assigned_at"] = last_assigned_at
        if not updates:
            return False

        def _sync_update(conn: sqlite3.Connection) -> bool:
            cursor = conn.cursor()
            assignments = ", ".join(f"{key} = ?" for key in updates)
            values = list(updates.values())
            values.extend([channel_id, account_email])
            cursor.execute(
                f"""
                UPDATE channel_account_relations
                SET {assignments}, updated_at = CURRENT_TIMESTAMP
                WHERE channel_id = ? AND account_email = ?
                """,
                values,
            )
            conn.commit()
            return cursor.rowcount > 0

        return await self._run_in_thread(_sync_update)

    async def list_channel_account_relations(
        self, channel_id: int
    ) -> list[dict[str, Any]]:
        def _sync_list(conn: sqlite3.Connection) -> list[dict[str, Any]]:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT
                    channel_id,
                    account_email,
                    status,
                    weight,
                    last_assigned_at,
                    created_at,
                    updated_at
                FROM channel_account_relations
                WHERE channel_id = ?
                ORDER BY weight DESC, account_email ASC
                """,
                (channel_id,),
            )
            return [dict(row) for row in cursor.fetchall()]

        return await self._run_in_thread(_sync_list)

    async def bind_resource_to_channel(
        self, channel_id: int, resource_id: int, status: str = "active"
    ) -> bool:
        def _sync_upsert(conn: sqlite3.Connection) -> bool:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO channel_resource_relations (channel_id, resource_id, status)
                VALUES (?, ?, ?)
                ON CONFLICT(channel_id, resource_id) DO UPDATE SET
                    status = excluded.status,
                    updated_at = CURRENT_TIMESTAMP
                """,
                (channel_id, resource_id, status),
            )
            conn.commit()
            return True

        return await self._run_in_thread(_sync_upsert)

    async def list_channel_resource_relations(
        self, channel_id: int
    ) -> list[dict[str, Any]]:
        def _sync_list(conn: sqlite3.Connection) -> list[dict[str, Any]]:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT
                    channel_id,
                    resource_id,
                    status,
                    created_at,
                    updated_at
                FROM channel_resource_relations
                WHERE channel_id = ?
                ORDER BY resource_id ASC
                """,
                (channel_id,),
            )
            return [dict(row) for row in cursor.fetchall()]

        return await self._run_in_thread(_sync_list)

    async def create_allocation_lease(
        self,
        channel_id: int,
        account_email: str,
        expires_at: str,
        leased_to: str = "",
        status: str = "active",
    ) -> int:
        def _sync_create(conn: sqlite3.Connection) -> int:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO allocation_leases (
                    channel_id, account_email, leased_to, expires_at, status
                ) VALUES (?, ?, ?, ?, ?)
                """,
                (channel_id, account_email, leased_to, expires_at, status),
            )
            conn.commit()
            return int(cursor.lastrowid)

        return await self._run_in_thread(_sync_create)

    async def get_active_allocation_lease(
        self, channel_id: int, account_email: str
    ) -> dict[str, Any] | None:
        def _sync_get(conn: sqlite3.Connection) -> dict[str, Any] | None:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT
                    id,
                    channel_id,
                    account_email,
                    leased_to,
                    leased_at,
                    expires_at,
                    status,
                    released_at,
                    created_at,
                    updated_at
                FROM allocation_leases
                WHERE channel_id = ? AND account_email = ? AND status = 'active'
                ORDER BY id DESC
                LIMIT 1
                """,
                (channel_id, account_email),
            )
            row = cursor.fetchone()
            return dict(row) if row else None

        return await self._run_in_thread(_sync_get)

    async def release_allocation_lease(self, lease_id: int) -> bool:
        def _sync_release(conn: sqlite3.Connection) -> bool:
            cursor = conn.cursor()
            cursor.execute(
                """
                UPDATE allocation_leases
                SET status = 'released',
                    released_at = CURRENT_TIMESTAMP,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ? AND status = 'active'
                """,
                (lease_id,),
            )
            conn.commit()
            return cursor.rowcount > 0

        return await self._run_in_thread(_sync_release)
