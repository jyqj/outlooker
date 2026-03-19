#!/usr/bin/env python3
"""Account operation audit database operations."""

from __future__ import annotations

import sqlite3
from typing import Any

from .base import RunInThreadMixin


class AccountOperationsMixin(RunInThreadMixin):
    """Mixin providing Outlook account operation audit helpers."""

    async def insert_account_operation_audit(
        self,
        email: str,
        operation: str,
        operator: str = "",
        result: str = "success",
        details: str = "",
        timestamp: str | None = None,
    ) -> int:
        def _sync_insert(conn: sqlite3.Connection) -> int:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO account_operation_audit (
                    email, operation, operator, result, details, timestamp
                ) VALUES (?, ?, ?, ?, ?, COALESCE(?, CURRENT_TIMESTAMP))
                """,
                (email, operation, operator, result, details, timestamp),
            )
            conn.commit()
            return int(cursor.lastrowid)

        return await self._run_in_thread(_sync_insert)

    async def list_account_operation_audits(
        self,
        email: str | None = None,
        operation: str | None = None,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        def _sync_list(conn: sqlite3.Connection) -> list[dict[str, Any]]:
            cursor = conn.cursor()
            conditions: list[str] = []
            params: list[Any] = []
            if email:
                conditions.append("email = ?")
                params.append(email)
            if operation:
                conditions.append("operation = ?")
                params.append(operation)

            where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""
            params.append(max(1, limit))
            cursor.execute(
                f"""
                SELECT
                    id,
                    email,
                    operation,
                    operator,
                    result,
                    details,
                    timestamp,
                    created_at
                FROM account_operation_audit
                {where_clause}
                ORDER BY id DESC
                LIMIT ?
                """,
                params,
            )
            return [dict(row) for row in cursor.fetchall()]

        return await self._run_in_thread(_sync_list)
