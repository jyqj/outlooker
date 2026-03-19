from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from app.services.outlook import binder


class _FakeResponse:
    def __init__(self, payload: dict[str, object], status_code: int = 200) -> None:
        self._payload = payload
        self.status_code = status_code
        self.text = "ok"

    def json(self):
        return self._payload


class _FakeAsyncClient:
    def __init__(self, response: _FakeResponse) -> None:
        self._response = response

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return None

    async def post(self, url: str, data: dict[str, str]):
        return self._response


@pytest.mark.asyncio
async def test_exchange_auth_code_persists_token(monkeypatch):
    monkeypatch.setattr(
        binder,
        "get_default_oauth_config",
        AsyncMock(
            return_value={
                "id": 3,
                "client_id": "client-id",
                "client_secret": "",
                "redirect_uri": "https://login.microsoftonline.com/common/oauth2/nativeclient",
                "scopes": "User.Read offline_access",
                "token_url": "https://login.microsoftonline.com/consumers/oauth2/v2.0/token",
            }
        ),
    )
    monkeypatch.setattr(binder, "resolve_channel_proxy", AsyncMock(return_value=None))
    monkeypatch.setattr(
        binder.httpx,
        "AsyncClient",
        lambda *args, **kwargs: _FakeAsyncClient(
            _FakeResponse(
                {
                    "access_token": "access-token",
                    "refresh_token": "refresh-token",
                    "expires_in": 3600,
                    "scope": "User.Read offline_access",
                }
            )
        ),
    )
    monkeypatch.setattr(binder.db_manager, "get_outlook_account", AsyncMock(return_value=None))
    monkeypatch.setattr(binder.db_manager, "create_outlook_account", AsyncMock(return_value=1))
    monkeypatch.setattr(binder.db_manager, "get_latest_active_oauth_token", AsyncMock(return_value=None))
    monkeypatch.setattr(binder.db_manager, "create_oauth_token", AsyncMock(return_value=9))
    monkeypatch.setattr(
        binder.db_manager,
        "get_oauth_token_by_id",
        AsyncMock(return_value={"id": 9, "scopes_granted": "User.Read offline_access"}),
    )
    monkeypatch.setattr(binder.db_manager, "get_account", AsyncMock(return_value={"email": "user@example.com"}))
    monkeypatch.setattr(binder.db_manager, "update_account", AsyncMock(return_value=True))

    from app.services.outlook import graph

    monkeypatch.setattr(graph, "sync_account_capabilities", AsyncMock(return_value={"graph_ready": True}))

    result = await binder._exchange_auth_code("auth-code", email="user@example.com", channel_id=None)

    assert result["token_id"] == 9
    binder.db_manager.create_oauth_token.assert_awaited_once()
    binder.db_manager.update_account.assert_awaited_once_with("user@example.com", refresh_token="refresh-token")
