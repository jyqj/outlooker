#!/usr/bin/env python3
"""Read-optimized, secret-free Outlook asset projections."""

from __future__ import annotations

import sqlite3
from typing import Any

from .base import RunInThreadMixin

MAX_OUTLOOK_ASSET_PAGE_SIZE = 200
MAX_RECENT_OPERATIONS = 100

_ACCOUNT_VIEW_SELECT = """
SELECT
    account.email AS account_email,
    account.status AS account_status,
    account.account_type AS account_type,
    account.source_account_email AS source_account_email,
    account.default_channel_id AS default_channel_id,
    account.notes AS notes,
    account.last_synced_at AS last_synced_at,
    account.created_at AS account_created_at,
    account.updated_at AS account_updated_at,
    capability.email AS capability_email,
    capability.imap_ready AS capability_imap_ready,
    capability.graph_ready AS capability_graph_ready,
    capability.protocol_ready AS capability_protocol_ready,
    capability.browser_fallback_ready AS capability_browser_fallback_ready,
    capability.updated_at AS capability_updated_at,
    token.id AS token_id,
    token.oauth_config_id AS token_oauth_config_id,
    token.email AS token_email,
    token.expires_at AS token_expires_at,
    token.scopes_granted AS token_scopes_granted,
    token.status AS token_status,
    token.last_error AS token_last_error,
    token.created_at AS token_created_at,
    token.updated_at AS token_updated_at,
    CASE
        WHEN token.access_token IS NOT NULL AND token.access_token <> '' THEN 1
        ELSE 0
    END AS token_has_access_token,
    CASE
        WHEN token.refresh_token IS NOT NULL AND token.refresh_token <> '' THEN 1
        ELSE 0
    END AS token_has_refresh_token
FROM outlook_accounts AS account
LEFT JOIN account_capabilities AS capability
    ON capability.email = account.email
LEFT JOIN oauth_tokens AS token
    ON token.id = (
        SELECT candidate.id
        FROM oauth_tokens AS candidate
        WHERE candidate.email = account.email
          AND candidate.status = 'active'
        ORDER BY candidate.id DESC
        LIMIT 1
    )
"""


def _normalize_page(limit: int, offset: int) -> tuple[int, int]:
    try:
        normalized_limit = int(limit)
    except (TypeError, ValueError):
        normalized_limit = 100
    try:
        normalized_offset = int(offset)
    except (TypeError, ValueError):
        normalized_offset = 0
    return (
        max(1, min(MAX_OUTLOOK_ASSET_PAGE_SIZE, normalized_limit)),
        max(0, normalized_offset),
    )


def _normalize_filter(value: str | None) -> str | None:
    normalized = (value or "").strip()
    return normalized or None


def _build_account_filters(
    status: str | None,
    account_type: str | None,
) -> tuple[str, list[Any]]:
    conditions: list[str] = []
    params: list[Any] = []

    normalized_status = _normalize_filter(status)
    normalized_account_type = _normalize_filter(account_type)
    if normalized_status:
        conditions.append("account.status = ?")
        params.append(normalized_status)
    if normalized_account_type:
        conditions.append("account.account_type = ?")
        params.append(normalized_account_type)

    where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""
    return where_clause, params


def _row_to_account_view(row: sqlite3.Row) -> dict[str, Any]:
    capabilities: dict[str, Any] | None = None
    if row["capability_email"] is not None:
        capabilities = {
            "email": row["capability_email"],
            "imap_ready": bool(row["capability_imap_ready"]),
            "graph_ready": bool(row["capability_graph_ready"]),
            "protocol_ready": bool(row["capability_protocol_ready"]),
            "browser_fallback_ready": bool(row["capability_browser_fallback_ready"]),
            "updated_at": row["capability_updated_at"],
        }

    token: dict[str, Any] | None = None
    if row["token_id"] is not None:
        token = {
            "id": int(row["token_id"]),
            "oauth_config_id": int(row["token_oauth_config_id"]),
            "email": row["token_email"],
            "expires_at": row["token_expires_at"],
            "scopes_granted": row["token_scopes_granted"],
            "status": row["token_status"],
            "last_error": row["token_last_error"],
            "created_at": row["token_created_at"],
            "updated_at": row["token_updated_at"],
            "has_access_token": bool(row["token_has_access_token"]),
            "has_refresh_token": bool(row["token_has_refresh_token"]),
        }

    return {
        "email": row["account_email"],
        "status": row["account_status"],
        "account_type": row["account_type"],
        "source_account_email": row["source_account_email"],
        "default_channel_id": row["default_channel_id"],
        "notes": row["notes"],
        "last_synced_at": row["last_synced_at"],
        "created_at": row["account_created_at"],
        "updated_at": row["account_updated_at"],
        "token": token,
        "capabilities": capabilities,
    }


class OutlookAssetReadMixin(RunInThreadMixin):
    """Build Outlook account list/detail views with one DB task per request."""

    async def list_outlook_account_views(
        self,
        status: str | None = None,
        account_type: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> dict[str, Any]:
        normalized_limit, normalized_offset = _normalize_page(limit, offset)
        where_clause, filter_params = _build_account_filters(status, account_type)

        def _sync_list(conn: sqlite3.Connection) -> dict[str, Any]:
            cursor = conn.cursor()
            cursor.execute("BEGIN")
            try:
                count_row = cursor.execute(
                    f"SELECT COUNT(*) FROM outlook_accounts AS account {where_clause}",
                    filter_params,
                ).fetchone()
                total = int(count_row[0]) if count_row else 0

                rows = cursor.execute(
                    f"""
                    {_ACCOUNT_VIEW_SELECT}
                    {where_clause}
                    ORDER BY account.updated_at DESC, account.email ASC
                    LIMIT ? OFFSET ?
                    """,
                    [*filter_params, normalized_limit, normalized_offset],
                ).fetchall()
                return {
                    "items": [_row_to_account_view(row) for row in rows],
                    "total": total,
                    "limit": normalized_limit,
                    "offset": normalized_offset,
                }
            finally:
                if conn.in_transaction:
                    conn.rollback()

        return await self._run_in_thread(_sync_list)

    async def get_outlook_account_detail_view(
        self,
        email: str,
        recent_operations_limit: int = 20,
    ) -> dict[str, Any] | None:
        normalized_email = email.strip()
        if not normalized_email:
            return None
        try:
            requested_audit_limit = int(recent_operations_limit)
        except (TypeError, ValueError):
            requested_audit_limit = 20
        normalized_audit_limit = max(
            1,
            min(MAX_RECENT_OPERATIONS, requested_audit_limit),
        )

        def _sync_detail(conn: sqlite3.Connection) -> dict[str, Any] | None:
            cursor = conn.cursor()
            cursor.execute("BEGIN")
            try:
                account_row = cursor.execute(
                    f"{_ACCOUNT_VIEW_SELECT} WHERE account.email = ?",
                    (normalized_email,),
                ).fetchone()
                if account_row is None:
                    return None

                profile_row = cursor.execute(
                    """
                    SELECT email, profile_json, synced_at, updated_at
                    FROM account_profiles_cache
                    WHERE email = ?
                    """,
                    (normalized_email,),
                ).fetchone()
                security_rows = cursor.execute(
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
                    (normalized_email,),
                ).fetchall()
                operation_rows = cursor.execute(
                    """
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
                    WHERE email = ?
                    ORDER BY id DESC
                    LIMIT ?
                    """,
                    (normalized_email, normalized_audit_limit),
                ).fetchall()

                detail = _row_to_account_view(account_row)
                detail["profile_cache"] = dict(profile_row) if profile_row else None
                detail["security_methods_snapshot"] = [dict(row) for row in security_rows]
                detail["recent_operations"] = [dict(row) for row in operation_rows]
                return detail
            finally:
                if conn.in_transaction:
                    conn.rollback()

        return await self._run_in_thread(_sync_detail)
