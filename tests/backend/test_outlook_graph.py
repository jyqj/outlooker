from __future__ import annotations

import json
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.outlook import graph, graph_token_service


@pytest.mark.asyncio
async def test_get_user_profile_uses_cache(monkeypatch):
    monkeypatch.setattr(
        graph.db_manager,
        "get_account_profile_cache",
        AsyncMock(return_value={"profile_json": json.dumps({"displayName": "Cached User"})}),
    )

    profile = await graph.get_user_profile("cached@example.com")

    assert profile["displayName"] == "Cached User"


@pytest.mark.asyncio
async def test_list_email_auth_methods_persists_snapshot(monkeypatch):
    monkeypatch.setattr(
        graph,
        "_call_graph",
        AsyncMock(return_value={"value": [{"id": "m1", "emailAddress": "recovery@example.com"}]}),
    )
    monkeypatch.setattr(graph.db_manager, "upsert_account_security_method_snapshot", AsyncMock(return_value=True))
    monkeypatch.setattr(graph.db_manager, "insert_account_operation_audit", AsyncMock(return_value=1))

    result = await graph.list_email_auth_methods("user@example.com")

    assert result["value"][0]["emailAddress"] == "recovery@example.com"
    graph.db_manager.upsert_account_security_method_snapshot.assert_awaited()


@pytest.mark.asyncio
async def test_update_mailbox_settings_refreshes_after_patch(monkeypatch):
    sequence = [
        {},
        {"timeZone": "UTC", "language": {"locale": "en-US"}},
    ]
    monkeypatch.setattr(
        graph,
        "_call_graph",
        AsyncMock(side_effect=sequence),
    )
    monkeypatch.setattr(graph.db_manager, "insert_account_operation_audit", AsyncMock(return_value=1))

    result = await graph.update_mailbox_settings("user@example.com", {"timeZone": "UTC"})

    assert result["timeZone"] == "UTC"


@pytest.mark.asyncio
async def test_list_risky_users_returns_graph_payload(monkeypatch):
    monkeypatch.setattr(
        graph,
        "_call_graph",
        AsyncMock(return_value={"value": [{"id": "risk-1"}]}),
    )
    monkeypatch.setattr(graph.db_manager, "insert_account_operation_audit", AsyncMock(return_value=1))

    result = await graph.list_risky_users("user@example.com")

    assert result["value"][0]["id"] == "risk-1"


@pytest.mark.asyncio
async def test_refresh_account_token_success(monkeypatch):
    token_record = {
        "id": 1,
        "oauth_config_id": 10,
        "email": "user@example.com",
        "refresh_token": "refresh-token",
        "status": "active",
    }
    config = {
        "id": 10,
        "client_id": "client-id",
        "client_secret": "",
        "token_url": "https://example.com/token",
        "scopes": "User.Read Mail.ReadWrite",
    }
    updated = {
        "id": 1,
        "oauth_config_id": 10,
        "email": "user@example.com",
        "access_token": "new-access-token",
        "refresh_token": "new-refresh-token",
        "expires_at": "2030-01-01T00:00:00+00:00",
        "status": "active",
    }

    monkeypatch.setattr(graph_token_service.db_manager, "get_latest_active_oauth_token", AsyncMock(return_value=token_record))
    monkeypatch.setattr(graph_token_service.db_manager, "get_oauth_token_by_id", AsyncMock(return_value=updated))
    monkeypatch.setattr(graph_token_service.db_manager, "update_oauth_token", AsyncMock(return_value=True))
    monkeypatch.setattr(graph_token_service, "get_oauth_config_by_id", AsyncMock(return_value=config))
    monkeypatch.setattr(graph_token_service, "resolve_channel_proxy", AsyncMock(return_value=None))

    response = MagicMock()
    response.status_code = 200
    response.json.return_value = {
        "access_token": "new-access-token",
        "refresh_token": "new-refresh-token",
        "expires_in": 3600,
        "scope": "User.Read Mail.ReadWrite",
    }

    with patch("app.services.outlook.graph_token_service.httpx.AsyncClient") as mock_client:
        instance = AsyncMock()
        instance.post.return_value = response
        instance.__aenter__.return_value = instance
        instance.__aexit__.return_value = None
        mock_client.return_value = instance

        result = await graph_token_service.refresh_account_token("user@example.com")

    assert result["access_token"] == "new-access-token"
