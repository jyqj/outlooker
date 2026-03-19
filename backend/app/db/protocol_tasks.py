#!/usr/bin/env python3
"""Protocol task database operations."""

from __future__ import annotations

import sqlite3
from typing import Any

from .base import RunInThreadMixin


class ProtocolTasksMixin(RunInThreadMixin):
    """Mixin providing minimal protocol task operations."""

    async def create_protocol_task(
        self,
        task_type: str,
        target_email: str,
        old_email: str = "",
        new_email: str = "",
        verification_email: str = "",
        channel_id: int | None = None,
        resource_id: int | None = None,
        status: str = "pending",
        retry_count: int = 0,
        error_message: str = "",
    ) -> int:
        def _sync_create(conn: sqlite3.Connection) -> int:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO protocol_tasks (
                    task_type, target_email, old_email, new_email, verification_email,
                    channel_id, resource_id, status, retry_count, error_message
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    task_type,
                    target_email,
                    old_email,
                    new_email,
                    verification_email,
                    channel_id,
                    resource_id,
                    status,
                    retry_count,
                    error_message,
                ),
            )
            conn.commit()
            return int(cursor.lastrowid)

        return await self._run_in_thread(_sync_create)

    async def get_protocol_task(self, task_id: int) -> dict[str, Any] | None:
        def _sync_get(conn: sqlite3.Connection) -> dict[str, Any] | None:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT
                    id,
                    task_type,
                    target_email,
                    old_email,
                    new_email,
                    verification_email,
                    channel_id,
                    resource_id,
                    status,
                    retry_count,
                    error_message,
                    created_at,
                    updated_at
                FROM protocol_tasks
                WHERE id = ?
                """,
                (task_id,),
            )
            row = cursor.fetchone()
            return dict(row) if row else None

        return await self._run_in_thread(_sync_get)

    async def update_protocol_task(self, task_id: int, **fields: Any) -> bool:
        allowed_fields = {
            "old_email",
            "new_email",
            "verification_email",
            "channel_id",
            "resource_id",
            "status",
            "retry_count",
            "error_message",
        }
        updates = {key: value for key, value in fields.items() if key in allowed_fields}
        if not updates:
            return False

        def _sync_update(conn: sqlite3.Connection) -> bool:
            cursor = conn.cursor()
            assignments = ", ".join(f"{key} = ?" for key in updates)
            values = list(updates.values())
            values.append(task_id)
            cursor.execute(
                f"""
                UPDATE protocol_tasks
                SET {assignments}, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                values,
            )
            conn.commit()
            return cursor.rowcount > 0

        return await self._run_in_thread(_sync_update)

    async def add_protocol_task_step(
        self,
        task_id: int,
        step: str,
        status: str = "pending",
        detail: str = "",
        started_at: str | None = None,
        finished_at: str | None = None,
    ) -> int:
        def _sync_create(conn: sqlite3.Connection) -> int:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO protocol_task_steps (
                    task_id, step, status, detail, started_at, finished_at
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (task_id, step, status, detail, started_at, finished_at),
            )
            conn.commit()
            return int(cursor.lastrowid)

        return await self._run_in_thread(_sync_create)

    async def list_protocol_task_steps(self, task_id: int) -> list[dict[str, Any]]:
        def _sync_list(conn: sqlite3.Connection) -> list[dict[str, Any]]:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT
                    id,
                    task_id,
                    step,
                    status,
                    detail,
                    started_at,
                    finished_at,
                    created_at,
                    updated_at
                FROM protocol_task_steps
                WHERE task_id = ?
                ORDER BY id ASC
                """,
                (task_id,),
            )
            return [dict(row) for row in cursor.fetchall()]

        return await self._run_in_thread(_sync_list)

    async def list_protocol_tasks(
        self,
        status: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        def _sync_list(conn: sqlite3.Connection) -> list[dict[str, Any]]:
            cursor = conn.cursor()
            params: list[Any] = []
            where_clause = ""
            if status:
                where_clause = "WHERE status = ?"
                params.append(status)
            params.extend([max(1, limit), max(0, offset)])
            cursor.execute(
                f"""
                SELECT
                    id,
                    task_type,
                    target_email,
                    old_email,
                    new_email,
                    verification_email,
                    channel_id,
                    resource_id,
                    status,
                    retry_count,
                    error_message,
                    created_at,
                    updated_at
                FROM protocol_tasks
                {where_clause}
                ORDER BY id DESC
                LIMIT ? OFFSET ?
                """,
                params,
            )
            return [dict(row) for row in cursor.fetchall()]

        return await self._run_in_thread(_sync_list)
