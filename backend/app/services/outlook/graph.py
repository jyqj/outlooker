"""Microsoft Graph client primitives and account-management operations."""

from __future__ import annotations

import json
from typing import Any

import httpx

from ...db import db_manager
from ...settings import get_settings
from ...utils.redaction import redact_log_data
from .errors import GraphAPIError
from .graph_token_service import get_valid_token

GRAPH_BASE = "https://graph.microsoft.com/v1.0"
GRAPH_BETA = "https://graph.microsoft.com/beta"

_settings = get_settings()


async def _record_operation(
    email: str,
    operation: str,
    result: str = "success",
    details: dict[str, Any] | None = None,
    operator: str = "system",
) -> None:
    payload = redact_log_data(details or {})
    await db_manager.insert_account_operation_audit(
        email=email,
        operation=operation,
        operator=operator,
        result=result,
        details=json.dumps(payload, ensure_ascii=False),
    )


async def _mark_graph_capability(email: str, ready: bool) -> None:
    existing = await db_manager.get_account_capabilities(email)
    await db_manager.upsert_account_capabilities(
        email=email,
        imap_ready=bool(existing["imap_ready"]) if existing else False,
        graph_ready=ready,
        protocol_ready=bool(existing["protocol_ready"]) if existing else False,
        browser_fallback_ready=bool(existing["browser_fallback_ready"]) if existing else False,
    )


def _parse_scopes(scopes_value: str | None) -> set[str]:
    return {scope.strip() for scope in (scopes_value or "").split() if scope.strip()}


async def sync_account_capabilities(
    email: str,
    token: dict[str, Any] | None = None,
    graph_error: GraphAPIError | None = None,
) -> dict[str, Any]:
    """Maintain account_capabilities based on account type, scopes, and Graph outcomes."""
    existing = await db_manager.get_account_capabilities(email)
    account = await db_manager.get_outlook_account(email)
    if token is None:
        token = await db_manager.get_latest_active_oauth_token(email)

    scopes = _parse_scopes(token.get("scopes_granted") if token else "")
    account_type = (account.get("account_type") if account else "consumer") or "consumer"
    has_graph_scope = bool(scopes.intersection({"User.Read", "Mail.ReadWrite", "Mail.Send", "MailboxSettings.ReadWrite"}))
    token_status = (token.get("status") if token else "") or ""
    graph_ready = account_type in {"consumer", "organization", "org", "work", "school"} and has_graph_scope
    if token_status and token_status != "active":
        graph_ready = False
    if graph_error is not None:
        graph_ready = False

    snapshot = {
        "imap_ready": bool(existing["imap_ready"]) if existing else False,
        "graph_ready": graph_ready,
        "protocol_ready": bool(existing["protocol_ready"]) if existing else False,
        "browser_fallback_ready": bool(existing["browser_fallback_ready"]) if existing else False,
    }
    await db_manager.upsert_account_capabilities(email=email, **snapshot)
    return snapshot


async def _graph_request(
    method: str,
    url: str,
    access_token: str,
    json_data: dict[str, Any] | None = None,
    params: dict[str, Any] | None = None,
    raw_response: bool = False,
    timeout: float = 30.0,
) -> Any:
    """Execute a Microsoft Graph request with normalized error handling."""
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
    }

    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.request(
                method,
                url,
                headers=headers,
                json=json_data,
                params=params,
            )
    except httpx.TimeoutException as exc:
        raise GraphAPIError(504, "Graph request timeout", "TIMEOUT") from exc
    except httpx.RequestError as exc:
        raise GraphAPIError(503, f"Graph request failed: {exc}", "REQUEST_ERROR") from exc

    if raw_response:
        return response

    if response.status_code == 204:
        return {}

    if response.status_code >= 400:
        try:
            payload = response.json()
        except ValueError as exc:
            raise GraphAPIError(
                response.status_code,
                response.text[:300] or "Unknown Graph error",
                "RAW_ERROR",
            ) from exc

        error_info = payload.get("error", {})
        raise GraphAPIError(
            response.status_code,
            error_info.get("message", response.text[:300] or "Unknown Graph error"),
            error_info.get("code", ""),
        )

    if not response.content:
        return {}

    try:
        return response.json()
    except ValueError as exc:
        raise GraphAPIError(response.status_code, "Invalid JSON response", "INVALID_JSON") from exc


async def _call_graph(
    email: str,
    method: str,
    url: str,
    json_data: dict[str, Any] | None = None,
    params: dict[str, Any] | None = None,
    raw_response: bool = False,
    timeout: float = 30.0,
) -> Any:
    access_token, _ = await get_valid_token(email)
    try:
        data = await _graph_request(
            method=method,
            url=url,
            access_token=access_token,
            json_data=json_data,
            params=params,
            raw_response=raw_response,
            timeout=timeout,
        )
        await sync_account_capabilities(email)
        return data
    except GraphAPIError as exc:
        await sync_account_capabilities(email, graph_error=exc)
        raise


async def get_user_profile(email: str, force_refresh: bool = False) -> dict[str, Any]:
    """Get the current user profile and update the local profile cache."""
    if not force_refresh:
        cached = await db_manager.get_account_profile_cache(email)
        if cached and cached.get("profile_json"):
            try:
                return json.loads(cached["profile_json"])
            except (TypeError, ValueError):
                pass

    params = {
        "$select": (
            "id,displayName,mail,userPrincipalName,mobilePhone,jobTitle,"
            "officeLocation,preferredLanguage,usageLocation,accountEnabled"
        )
    }
    profile = await _call_graph(email, "GET", f"{GRAPH_BASE}/me", params=params)
    await db_manager.upsert_account_profile_cache(email, profile)
    await _record_operation(email, "get_user_profile", "success", {"force_refresh": force_refresh})
    return profile


async def update_user_profile(email: str, updates: dict[str, Any]) -> dict[str, Any]:
    """Update the current user profile and refresh the local cache."""
    await _call_graph(email, "PATCH", f"{GRAPH_BASE}/me", json_data=updates)
    profile = await get_user_profile(email, force_refresh=True)
    await _record_operation(email, "update_user_profile", "success", {"updates": updates})
    return profile


async def get_mailbox_settings(email: str) -> dict[str, Any]:
    settings = await _call_graph(email, "GET", f"{GRAPH_BASE}/me/mailboxSettings")
    await _record_operation(email, "get_mailbox_settings", "success")
    return settings


async def update_mailbox_settings(email: str, updates: dict[str, Any]) -> dict[str, Any]:
    await _call_graph(email, "PATCH", f"{GRAPH_BASE}/me/mailboxSettings", json_data=updates)
    result = await get_mailbox_settings(email)
    await _record_operation(email, "update_mailbox_settings", "success", {"updates": updates})
    return result


async def get_regional_settings(email: str) -> dict[str, Any]:
    settings = await _call_graph(email, "GET", f"{GRAPH_BETA}/me/settings/regionalAndLanguageSettings")
    await _record_operation(email, "get_regional_settings", "success")
    return settings


async def update_regional_settings(email: str, updates: dict[str, Any]) -> dict[str, Any]:
    await _call_graph(
        email,
        "PATCH",
        f"{GRAPH_BETA}/me/settings/regionalAndLanguageSettings",
        json_data=updates,
    )
    result = await get_regional_settings(email)
    await _record_operation(email, "update_regional_settings", "success", {"updates": updates})
    return result


async def list_auth_methods(email: str) -> dict[str, Any]:
    data = await _call_graph(email, "GET", f"{GRAPH_BASE}/me/authentication/methods")
    await _record_operation(email, "list_auth_methods", "success")
    return data


async def list_email_auth_methods(email: str) -> dict[str, Any]:
    data = await _call_graph(email, "GET", f"{GRAPH_BASE}/me/authentication/emailMethods")
    for item in data.get("value", []):
        await db_manager.upsert_account_security_method_snapshot(
            email=email,
            method_type="email",
            method_id=item.get("id", ""),
            display_value=item.get("emailAddress", ""),
            status="active",
            raw_json=item,
        )
    await _record_operation(email, "list_email_auth_methods", "success")
    return data


async def add_email_auth_method(email: str, recovery_email: str) -> dict[str, Any]:
    data = await _call_graph(
        email,
        "POST",
        f"{GRAPH_BASE}/me/authentication/emailMethods",
        json_data={"emailAddress": recovery_email},
    )
    await db_manager.upsert_account_security_method_snapshot(
        email=email,
        method_type="email",
        method_id=data.get("id", ""),
        display_value=data.get("emailAddress", recovery_email),
        status="active",
        raw_json=data,
    )
    await _record_operation(email, "add_email_auth_method", "success", {"recovery_email": recovery_email})
    return data


async def update_email_auth_method(email: str, method_id: str, new_email: str) -> dict[str, Any]:
    await _call_graph(
        email,
        "PATCH",
        f"{GRAPH_BASE}/me/authentication/emailMethods/{method_id}",
        json_data={"emailAddress": new_email},
    )
    data = {"id": method_id, "emailAddress": new_email}
    await db_manager.upsert_account_security_method_snapshot(
        email=email,
        method_type="email",
        method_id=method_id,
        display_value=new_email,
        status="active",
        raw_json=data,
    )
    await _record_operation(
        email,
        "update_email_auth_method",
        "success",
        {"method_id": method_id, "new_email": new_email},
    )
    return data


async def delete_email_auth_method(email: str, method_id: str) -> dict[str, Any]:
    await _call_graph(email, "DELETE", f"{GRAPH_BASE}/me/authentication/emailMethods/{method_id}")
    await db_manager.upsert_account_security_method_snapshot(
        email=email,
        method_type="email",
        method_id=method_id,
        display_value="",
        status="deleted",
        raw_json={},
    )
    await _record_operation(email, "delete_email_auth_method", "success", {"method_id": method_id})
    return {"id": method_id, "deleted": True}


async def list_software_oath_methods(email: str) -> dict[str, Any]:
    data = await _call_graph(email, "GET", f"{GRAPH_BASE}/me/authentication/softwareOathMethods")
    for item in data.get("value", []):
        await db_manager.upsert_account_security_method_snapshot(
            email=email,
            method_type="totp",
            method_id=item.get("id", ""),
            display_value=item.get("displayName", item.get("id", "")),
            status="active",
            raw_json=item,
        )
    await _record_operation(email, "list_software_oath_methods", "success")
    return data


async def delete_software_oath_method(email: str, method_id: str) -> dict[str, Any]:
    await _call_graph(
        email,
        "DELETE",
        f"{GRAPH_BASE}/me/authentication/softwareOathMethods/{method_id}",
    )
    await db_manager.upsert_account_security_method_snapshot(
        email=email,
        method_type="totp",
        method_id=method_id,
        display_value="",
        status="deleted",
        raw_json={},
    )
    await _record_operation(email, "delete_software_oath_method", "success", {"method_id": method_id})
    return {"id": method_id, "deleted": True}


async def list_phone_methods(email: str) -> dict[str, Any]:
    data = await _call_graph(email, "GET", f"{GRAPH_BASE}/me/authentication/phoneMethods")
    for item in data.get("value", []):
        await db_manager.upsert_account_security_method_snapshot(
            email=email,
            method_type="phone",
            method_id=item.get("id", ""),
            display_value=item.get("phoneNumber", ""),
            status="active",
            raw_json=item,
        )
    await _record_operation(email, "list_phone_methods", "success")
    return data


async def add_phone_method(email: str, phone_number: str, phone_type: str = "mobile") -> dict[str, Any]:
    data = await _call_graph(
        email,
        "POST",
        f"{GRAPH_BASE}/me/authentication/phoneMethods",
        json_data={"phoneNumber": phone_number, "phoneType": phone_type},
    )
    await db_manager.upsert_account_security_method_snapshot(
        email=email,
        method_type="phone",
        method_id=data.get("id", ""),
        display_value=data.get("phoneNumber", phone_number),
        status="active",
        raw_json=data,
    )
    await _record_operation(
        email,
        "add_phone_method",
        "success",
        {"phone_number": phone_number, "phone_type": phone_type},
    )
    return data


async def get_auth_methods_bundle(email: str) -> dict[str, Any]:
    """Aggregate auth methods into one response for the account detail page."""
    methods = await list_auth_methods(email)
    email_methods = await list_email_auth_methods(email)
    totp_methods = await list_software_oath_methods(email)
    phone_methods = await list_phone_methods(email)
    return {
        "methods": methods.get("value", []),
        "email_methods": email_methods.get("value", []),
        "totp_methods": totp_methods.get("value", []),
        "phone_methods": phone_methods.get("value", []),
    }


async def change_password(email: str, current_password: str, new_password: str) -> dict[str, Any]:
    await _call_graph(
        email,
        "POST",
        f"{GRAPH_BASE}/me/changePassword",
        json_data={"currentPassword": current_password, "newPassword": new_password},
    )
    await _record_operation(email, "change_password", "success")
    return {"changed": True}


async def revoke_sessions(email: str) -> dict[str, Any]:
    data = await _call_graph(email, "POST", f"{GRAPH_BASE}/me/revokeSignInSessions")
    await _record_operation(email, "revoke_sessions", "success")
    return data


async def list_risky_users(email: str) -> dict[str, Any]:
    data = await _call_graph(email, "GET", f"{GRAPH_BASE}/identityProtection/riskyUsers")
    await _record_operation(email, "list_risky_users", "success")
    return data


async def dismiss_risky_user(email: str, user_id: str) -> dict[str, Any]:
    data = await _call_graph(
        email,
        "POST",
        f"{GRAPH_BASE}/identityProtection/riskyUsers/dismiss",
        json_data={"userIds": [user_id]},
    )
    await _record_operation(email, "dismiss_risky_user", "success", {"user_id": user_id})
    return data


def ensure_graph_capability(email: str, capability: str = "graph") -> None:
    """Guard helper for routers/services that require Graph support."""
    if not _settings.outlook_features.graph_enabled:
        raise GraphAPIError(503, "Graph account management is disabled", "FEATURE_DISABLED")
    if capability != "graph":
        return


async def ensure_graph_operation_ready(email: str) -> dict[str, Any]:
    """Ensure a specific Outlook account is ready for Graph operations."""
    ensure_graph_capability(email, "graph")

    account = await db_manager.get_outlook_account(email)
    if account is None:
        raise GraphAPIError(404, f"Outlook account not found: {email}", "OUTLOOK_ACCOUNT_NOT_FOUND")

    capabilities = await db_manager.get_account_capabilities(email)
    if capabilities is None:
        token = await db_manager.get_latest_active_oauth_token(email)
        capabilities = await sync_account_capabilities(email, token=token)

    if not capabilities.get("graph_ready"):
        raise GraphAPIError(
            409,
            f"Graph capability is not ready for account: {email}",
            "GRAPH_CAPABILITY_NOT_READY",
        )
    return capabilities
