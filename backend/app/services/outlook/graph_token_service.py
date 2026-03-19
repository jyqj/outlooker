"""OAuth token configuration helpers for Outlook Graph access."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta
from typing import Any

import httpx

from ...db import db_manager
from ...settings import get_settings
from ..channeling.allocation_service import resolve_channel_proxy
from .errors import GraphAPIError

DEFAULT_PUBLIC_CLIENT_ID = "dbc8e03a-b00c-46bd-ae65-b683e7707cb0"
DEFAULT_PUBLIC_SCOPES = (
    "openid profile email offline_access "
    "Mail.ReadWrite Mail.Send MailboxSettings.ReadWrite User.Read"
)

_settings = get_settings()


async def get_oauth_config_by_id(config_id: int) -> dict[str, Any] | None:
    """Load an OAuth config by primary key."""
    return await db_manager.get_oauth_config_by_id(config_id)


async def get_oauth_config_by_client_id(client_id: str) -> dict[str, Any] | None:
    """Load an OAuth config by client_id."""
    return await db_manager.get_oauth_config_by_client_id(client_id)


async def get_default_oauth_config(client_id: str | None = None) -> dict[str, Any]:
    """Return the default public-client OAuth configuration, creating it if missing."""
    resolved_client_id = (client_id or _settings.client_id or DEFAULT_PUBLIC_CLIENT_ID).strip()
    existing = await db_manager.get_oauth_config_by_client_id(resolved_client_id)
    if existing:
        return existing

    config_id = await db_manager.create_oauth_config(
        provider="microsoft",
        name="Browser OAuth (Public Client)",
        client_id=resolved_client_id,
        client_secret="",
        tenant_id="consumers",
        redirect_uri="https://login.microsoftonline.com/common/oauth2/nativeclient",
        scopes=DEFAULT_PUBLIC_SCOPES,
        authorization_url="https://login.microsoftonline.com/consumers/oauth2/v2.0/authorize",
        token_url="https://login.microsoftonline.com/consumers/oauth2/v2.0/token",
        status="active",
    )
    created = await db_manager.get_oauth_config_by_id(config_id)
    if not created:
        raise RuntimeError("Failed to create default OAuth config")
    return created


async def get_oauth_config_for_email(email: str) -> dict[str, Any] | None:
    """Resolve an OAuth config for the given email via its latest active token."""
    token = await db_manager.get_latest_active_oauth_token(email)
    if token and token.get("oauth_config_id"):
        return await db_manager.get_oauth_config_by_id(int(token["oauth_config_id"]))
    return None


async def promote_legacy_account_token(email: str) -> dict[str, Any] | None:
    """Promote a legacy account refresh_token into the new oauth_tokens table."""
    existing = await db_manager.get_latest_active_oauth_token(email)
    if existing:
        return existing

    legacy_account = await db_manager.get_account(email)
    if not legacy_account or not legacy_account.get("refresh_token"):
        return None

    if not await db_manager.get_outlook_account(email):
        await db_manager.create_outlook_account(
            email=email,
            status="active",
            account_type="consumer",
            source_account_email=email,
            notes="auto-created during legacy token promotion",
        )

    config = await get_default_oauth_config(legacy_account.get("client_id") or None)
    token_id = await db_manager.create_oauth_token(
        oauth_config_id=int(config["id"]),
        email=email,
        access_token="",
        refresh_token=legacy_account["refresh_token"],
        expires_at=None,
        scopes_granted=config.get("scopes", ""),
        status="active",
        last_error="",
    )
    return await db_manager.get_oauth_token_by_id(token_id)


def _parse_expires_at(value: str | None) -> datetime | None:
    if not value:
        return None
    normalized = value.replace("Z", "+00:00")
    parsed = datetime.fromisoformat(normalized)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


async def _refresh_token_record(token: dict[str, Any], *, proxy_url: str | None = None) -> dict[str, Any]:
    refresh_token = (token.get("refresh_token") or "").strip()
    if not refresh_token:
        await db_manager.update_oauth_token(
            int(token["id"]),
            status="expired",
            last_error="missing refresh_token",
        )
        raise GraphAPIError(401, "令牌已过期且无 refresh_token", "TOKEN_EXPIRED")

    config = await get_oauth_config_by_id(int(token["oauth_config_id"]))
    if not config:
        config = await get_default_oauth_config()

    token_url = config.get("token_url") or "https://login.microsoftonline.com/common/oauth2/v2.0/token"
    post_data: dict[str, str] = {
        "client_id": config.get("client_id") or DEFAULT_PUBLIC_CLIENT_ID,
        "refresh_token": refresh_token,
        "grant_type": "refresh_token",
        "scope": config.get("scopes") or DEFAULT_PUBLIC_SCOPES,
    }
    if config.get("client_secret"):
        post_data["client_secret"] = config["client_secret"]

    try:
        async with httpx.AsyncClient(timeout=15.0, proxy=proxy_url) as client:
            response = await client.post(token_url, data=post_data)
    except httpx.TimeoutException as exc:
        await db_manager.update_oauth_token(int(token["id"]), last_error="refresh timeout")
        raise GraphAPIError(504, "刷新令牌超时", "TIMEOUT") from exc
    except httpx.RequestError as exc:
        await db_manager.update_oauth_token(int(token["id"]), last_error=str(exc))
        raise GraphAPIError(503, f"刷新令牌失败: {exc}", "REQUEST_ERROR") from exc

    if response.status_code != 200:
        await db_manager.update_oauth_token(
            int(token["id"]),
            status="expired",
            last_error=response.text[:300],
        )
        raise GraphAPIError(502, f"刷新令牌失败: {response.text[:200]}", "REFRESH_FAILED")

    payload = response.json()
    expires_in = int(payload.get("expires_in", 3600))
    new_expires_at = (datetime.now(UTC) + timedelta(seconds=expires_in)).isoformat()
    await db_manager.update_oauth_token(
        int(token["id"]),
        access_token=payload.get("access_token", ""),
        refresh_token=payload.get("refresh_token") or refresh_token,
        expires_at=new_expires_at,
        scopes_granted=payload.get("scope", config.get("scopes", "")),
        status="active",
        last_error="",
    )
    refreshed = await db_manager.get_oauth_token_by_id(int(token["id"]))
    if not refreshed or not refreshed.get("access_token"):
        raise GraphAPIError(500, "刷新后未能读取新的 access token", "TOKEN_READBACK_FAILED")
    return refreshed


async def get_valid_token(email: str, *, channel_id: int | None = None) -> tuple[str, dict[str, Any]]:
    """Load a valid Graph access token for an Outlook account."""
    token = await db_manager.get_latest_active_oauth_token(email)
    if not token:
        token = await promote_legacy_account_token(email)
    if not token:
        raise GraphAPIError(401, f"未找到 {email} 的有效 OAuth 令牌", "NO_TOKEN")

    expires_at = _parse_expires_at(token.get("expires_at"))
    has_usable_access_token = bool(token.get("access_token"))
    if has_usable_access_token and expires_at and expires_at > datetime.now(UTC) + timedelta(minutes=5):
        return token["access_token"], token

    proxy_url = await resolve_channel_proxy(channel_id)
    refreshed = await _refresh_token_record(token, proxy_url=proxy_url)
    return refreshed["access_token"], refreshed


async def refresh_account_token(email: str, *, channel_id: int | None = None) -> dict[str, Any]:
    """Force-refresh the latest active token for a single Outlook account."""
    token = await db_manager.get_latest_active_oauth_token(email)
    if not token:
        token = await promote_legacy_account_token(email)
    if not token:
        raise GraphAPIError(401, f"未找到 {email} 的可刷新令牌", "NO_TOKEN")
    proxy_url = await resolve_channel_proxy(channel_id)
    return await _refresh_token_record(token, proxy_url=proxy_url)


async def batch_refresh_account_tokens(
    emails: list[str] | None = None,
    limit: int = 100,
    offset: int = 0,
    concurrency: int = 5,
    channel_id: int | None = None,
) -> dict[str, Any]:
    """Batch-refresh Outlook account tokens and return an aggregated summary."""
    if emails is None:
        accounts = await db_manager.list_outlook_accounts(limit=limit, offset=offset)
        emails = [account["email"] for account in accounts]

    summary: dict[str, Any] = {
        "requested": len(emails),
        "refreshed": 0,
        "failed": 0,
        "details": [],
    }
    if not emails:
        return summary

    semaphore = asyncio.Semaphore(max(1, concurrency))

    async def _refresh_one(email: str) -> None:
        async with semaphore:
            try:
                refreshed = await refresh_account_token(email, channel_id=channel_id)
                summary["refreshed"] += 1
                summary["details"].append(
                    {
                        "email": email,
                        "status": "success",
                        "expires_at": refreshed.get("expires_at"),
                    }
                )
            except Exception as exc:  # noqa: BLE001
                summary["failed"] += 1
                summary["details"].append(
                    {
                        "email": email,
                        "status": "failed",
                        "error": str(exc),
                    }
                )

    await asyncio.gather(*[_refresh_one(email) for email in emails])
    return summary
