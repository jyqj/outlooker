#!/usr/bin/env python3
"""OAuth configuration and token database operations."""

from __future__ import annotations

import sqlite3
from typing import Any

from ..auth.security import decrypt_if_needed, encrypt_if_needed
from .base import RunInThreadMixin


def _normalize_oauth_config_row(row: sqlite3.Row | None) -> dict[str, Any] | None:
    if not row:
        return None
    data = dict(row)
    data["client_secret"] = decrypt_if_needed(data.get("client_secret") or "")
    return data


def _normalize_oauth_token_row(row: sqlite3.Row | None) -> dict[str, Any] | None:
    if not row:
        return None
    data = dict(row)
    data["access_token"] = decrypt_if_needed(data.get("access_token") or "")
    data["refresh_token"] = decrypt_if_needed(data.get("refresh_token") or "")
    return data


class OAuthTokensMixin(RunInThreadMixin):
    """Mixin providing minimal OAuth config and token operations."""

    async def create_oauth_config(
        self,
        provider: str,
        name: str,
        client_id: str,
        client_secret: str = "",
        tenant_id: str = "",
        redirect_uri: str = "",
        scopes: str = "",
        authorization_url: str = "",
        token_url: str = "",
        status: str = "active",
    ) -> int:
        def _sync_create(conn: sqlite3.Connection) -> int:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO oauth_configs (
                    provider, name, client_id, client_secret, tenant_id, redirect_uri,
                    scopes, authorization_url, token_url, status
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    provider,
                    name,
                    client_id,
                    encrypt_if_needed(client_secret),
                    tenant_id,
                    redirect_uri,
                    scopes,
                    authorization_url,
                    token_url,
                    status,
                ),
            )
            conn.commit()
            return int(cursor.lastrowid)

        return await self._run_in_thread(_sync_create)

    async def get_oauth_config_by_id(self, config_id: int) -> dict[str, Any] | None:
        def _sync_get(conn: sqlite3.Connection) -> dict[str, Any] | None:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT
                    id,
                    provider,
                    name,
                    client_id,
                    client_secret,
                    tenant_id,
                    redirect_uri,
                    scopes,
                    authorization_url,
                    token_url,
                    status,
                    created_at,
                    updated_at
                FROM oauth_configs
                WHERE id = ?
                """,
                (config_id,),
            )
            row = cursor.fetchone()
            return _normalize_oauth_config_row(row)

        return await self._run_in_thread(_sync_get)

    async def get_oauth_config_by_client_id(self, client_id: str) -> dict[str, Any] | None:
        def _sync_get(conn: sqlite3.Connection) -> dict[str, Any] | None:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT
                    id,
                    provider,
                    name,
                    client_id,
                    client_secret,
                    tenant_id,
                    redirect_uri,
                    scopes,
                    authorization_url,
                    token_url,
                    status,
                    created_at,
                    updated_at
                FROM oauth_configs
                WHERE client_id = ?
                """,
                (client_id,),
            )
            row = cursor.fetchone()
            return _normalize_oauth_config_row(row)

        return await self._run_in_thread(_sync_get)

    async def list_oauth_configs(
        self, provider: str | None = None, status: str | None = None
    ) -> list[dict[str, Any]]:
        def _sync_list(conn: sqlite3.Connection) -> list[dict[str, Any]]:
            cursor = conn.cursor()
            conditions: list[str] = []
            params: list[Any] = []
            if provider:
                conditions.append("provider = ?")
                params.append(provider)
            if status:
                conditions.append("status = ?")
                params.append(status)

            where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""
            cursor.execute(
                f"""
                SELECT
                    id,
                    provider,
                    name,
                    client_id,
                    client_secret,
                    tenant_id,
                    redirect_uri,
                    scopes,
                    authorization_url,
                    token_url,
                    status,
                    created_at,
                    updated_at
                FROM oauth_configs
                {where_clause}
                ORDER BY id ASC
                """,
                params,
            )
            return [_normalize_oauth_config_row(row) for row in cursor.fetchall()]

        return await self._run_in_thread(_sync_list)

    async def create_oauth_token(
        self,
        oauth_config_id: int,
        email: str,
        access_token: str = "",
        refresh_token: str = "",
        expires_at: str | None = None,
        scopes_granted: str = "",
        status: str = "active",
        last_error: str = "",
    ) -> int:
        def _sync_create(conn: sqlite3.Connection) -> int:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO oauth_tokens (
                    oauth_config_id, email, access_token, refresh_token,
                    expires_at, scopes_granted, status, last_error
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    oauth_config_id,
                    email,
                    encrypt_if_needed(access_token),
                    encrypt_if_needed(refresh_token),
                    expires_at,
                    scopes_granted,
                    status,
                    last_error,
                ),
            )
            conn.commit()
            return int(cursor.lastrowid)

        return await self._run_in_thread(_sync_create)

    async def get_latest_active_oauth_token(self, email: str) -> dict[str, Any] | None:
        def _sync_get(conn: sqlite3.Connection) -> dict[str, Any] | None:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT
                    id,
                    oauth_config_id,
                    email,
                    access_token,
                    refresh_token,
                    expires_at,
                    scopes_granted,
                    status,
                    last_error,
                    created_at,
                    updated_at
                FROM oauth_tokens
                WHERE email = ? AND status = 'active'
                ORDER BY id DESC
                LIMIT 1
                """,
                (email,),
            )
            row = cursor.fetchone()
            return _normalize_oauth_token_row(row)

        return await self._run_in_thread(_sync_get)

    async def get_oauth_token_by_id(self, token_id: int) -> dict[str, Any] | None:
        def _sync_get(conn: sqlite3.Connection) -> dict[str, Any] | None:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT
                    id,
                    oauth_config_id,
                    email,
                    access_token,
                    refresh_token,
                    expires_at,
                    scopes_granted,
                    status,
                    last_error,
                    created_at,
                    updated_at
                FROM oauth_tokens
                WHERE id = ?
                """,
                (token_id,),
            )
            row = cursor.fetchone()
            return _normalize_oauth_token_row(row)

        return await self._run_in_thread(_sync_get)

    async def list_oauth_tokens(
        self, email: str | None = None, status: str | None = None
    ) -> list[dict[str, Any]]:
        def _sync_list(conn: sqlite3.Connection) -> list[dict[str, Any]]:
            cursor = conn.cursor()
            conditions: list[str] = []
            params: list[Any] = []
            if email:
                conditions.append("email = ?")
                params.append(email)
            if status:
                conditions.append("status = ?")
                params.append(status)

            where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""
            cursor.execute(
                f"""
                SELECT
                    id,
                    oauth_config_id,
                    email,
                    access_token,
                    refresh_token,
                    expires_at,
                    scopes_granted,
                    status,
                    last_error,
                    created_at,
                    updated_at
                FROM oauth_tokens
                {where_clause}
                ORDER BY id DESC
                """,
                params,
            )
            return [_normalize_oauth_token_row(row) for row in cursor.fetchall()]

        return await self._run_in_thread(_sync_list)

    async def update_oauth_token(self, token_id: int, **fields: Any) -> bool:
        allowed_fields = {
            "access_token",
            "refresh_token",
            "expires_at",
            "scopes_granted",
            "status",
            "last_error",
        }
        updates = {key: value for key, value in fields.items() if key in allowed_fields}
        if not updates:
            return False
        if "access_token" in updates:
            updates["access_token"] = encrypt_if_needed(updates["access_token"])
        if "refresh_token" in updates:
            updates["refresh_token"] = encrypt_if_needed(updates["refresh_token"])

        def _sync_update(conn: sqlite3.Connection) -> bool:
            cursor = conn.cursor()
            assignments = ", ".join(f"{key} = ?" for key in updates)
            values = list(updates.values())
            values.append(token_id)
            cursor.execute(
                f"""
                UPDATE oauth_tokens
                SET {assignments}, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                values,
            )
            conn.commit()
            return cursor.rowcount > 0

        return await self._run_in_thread(_sync_update)
