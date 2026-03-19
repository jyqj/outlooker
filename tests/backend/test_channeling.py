from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from app.services.channeling import allocation_service


@pytest.mark.asyncio
async def test_bind_accounts_to_channel_counts_failures(monkeypatch):
    monkeypatch.setattr(
        allocation_service.db_manager,
        "get_outlook_account",
        AsyncMock(side_effect=[{"email": "ok@example.com"}, None]),
    )
    monkeypatch.setattr(
        allocation_service.db_manager,
        "bind_account_to_channel",
        AsyncMock(return_value=True),
    )

    result = await allocation_service.bind_accounts_to_channel(
        1,
        ["ok@example.com", "missing@example.com"],
    )

    assert result["updated"] == 1
    assert result["failed"] == 1


@pytest.mark.asyncio
async def test_report_channel_account_failure_quarantines_and_releases(monkeypatch):
    monkeypatch.setattr(
        allocation_service.db_manager,
        "get_channel_account_relation",
        AsyncMock(return_value={"status": "active"}),
    )
    monkeypatch.setattr(
        allocation_service.db_manager,
        "update_channel_account_relation",
        AsyncMock(return_value=True),
    )
    monkeypatch.setattr(
        allocation_service.db_manager,
        "get_active_allocation_lease",
        AsyncMock(return_value={"id": 7}),
    )
    monkeypatch.setattr(
        allocation_service.db_manager,
        "release_allocation_lease",
        AsyncMock(return_value=True),
    )

    result = await allocation_service.report_channel_account_failure(1, "user@example.com")

    assert result["status"] == "quarantine"
    allocation_service.db_manager.release_allocation_lease.assert_awaited_with(7)


@pytest.mark.asyncio
async def test_resolve_channel_proxy_returns_value(monkeypatch):
    monkeypatch.setattr(
        allocation_service.db_manager,
        "get_channel",
        AsyncMock(return_value={"proxy_url": "http://127.0.0.1:8080"}),
    )

    proxy = await allocation_service.resolve_channel_proxy(3)

    assert proxy == "http://127.0.0.1:8080"
