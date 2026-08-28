from __future__ import annotations

from contextlib import closing
from unittest.mock import AsyncMock

import pytest
from app.db.manager import DatabaseManager
from app.schemas.outlook_accounts import BatchRefreshRequest
from app.services.outlook import graph_token_service
from app.services.outlook.token_views import to_public_oauth_token
from pydantic import ValidationError as PydanticValidationError


@pytest.fixture
def asset_db(tmp_path):
    database = DatabaseManager(str(tmp_path / "outlook-assets.sqlite3"))
    yield database
    database.close()


async def _seed_asset(
    database: DatabaseManager,
    email: str = "asset@example.com",
) -> tuple[int, int]:
    await database.add_account(email, refresh_token=f"legacy-refresh-{email}")
    await database.create_outlook_account(
        email=email,
        status="active",
        account_type="consumer",
        source_account_email=email,
        notes="seeded asset",
    )
    await database.upsert_account_capabilities(
        email,
        imap_ready=True,
        graph_ready=True,
        protocol_ready=False,
        browser_fallback_ready=True,
    )
    config_id = await database.create_oauth_config(
        provider="microsoft",
        name="test",
        client_id=f"client-{email}",
    )
    first_token_id = await database.create_oauth_token(
        oauth_config_id=config_id,
        email=email,
        access_token="old-access-secret",
        refresh_token="old-refresh-secret",
        expires_at="2030-01-01T00:00:00+00:00",
        status="active",
    )
    latest_token_id = await database.create_oauth_token(
        oauth_config_id=config_id,
        email=email,
        access_token="latest-access-secret",
        refresh_token="latest-refresh-secret",
        expires_at="2031-01-01T00:00:00+00:00",
        scopes_granted="User.Read Mail.ReadWrite",
        status="active",
    )
    return first_token_id, latest_token_id


@pytest.mark.asyncio
async def test_list_asset_view_uses_one_db_task_and_never_returns_secrets(
    asset_db,
    monkeypatch,
):
    _, latest_token_id = await _seed_asset(asset_db)
    original_run_in_thread = asset_db._run_in_thread
    calls = 0

    async def counting_run_in_thread(handler):
        nonlocal calls
        calls += 1
        return await original_run_in_thread(handler)

    monkeypatch.setattr(asset_db, "_run_in_thread", counting_run_in_thread)
    page = await asset_db.list_outlook_account_views(limit=999, offset=-10)

    assert calls == 1
    assert page["total"] == 1
    assert page["limit"] == 200
    assert page["offset"] == 0
    item = page["items"][0]
    assert item["capabilities"]["graph_ready"] is True
    assert item["token"]["id"] == latest_token_id
    assert item["token"]["has_access_token"] is True
    assert item["token"]["has_refresh_token"] is True
    assert "access_token" not in item["token"]
    assert "refresh_token" not in item["token"]
    assert "latest-access-secret" not in repr(page)
    assert "latest-refresh-secret" not in repr(page)


@pytest.mark.asyncio
async def test_list_asset_view_filters_and_reports_total(asset_db):
    await _seed_asset(asset_db, "active@example.com")
    await asset_db.create_outlook_account(
        email="suspended@example.com",
        status="suspended",
        account_type="org",
    )

    active_page = await asset_db.list_outlook_account_views(status=" active ")
    org_page = await asset_db.list_outlook_account_views(account_type="org")

    assert active_page["total"] == 1
    assert [item["email"] for item in active_page["items"]] == ["active@example.com"]
    assert org_page["total"] == 1
    assert [item["email"] for item in org_page["items"]] == ["suspended@example.com"]


@pytest.mark.asyncio
async def test_detail_asset_view_aggregates_snapshot_in_one_db_task(
    asset_db,
    monkeypatch,
):
    await _seed_asset(asset_db)
    await asset_db.upsert_account_profile_cache(
        "asset@example.com",
        {"displayName": "Asset User"},
    )
    await asset_db.upsert_account_security_method_snapshot(
        "asset@example.com",
        method_type="email",
        method_id="method-1",
        display_value="recovery@example.com",
        raw_json={"id": "method-1"},
    )
    await asset_db.insert_account_operation_audit(
        "asset@example.com",
        operation="profile.read",
        details="ok",
    )

    original_run_in_thread = asset_db._run_in_thread
    calls = 0

    async def counting_run_in_thread(handler):
        nonlocal calls
        calls += 1
        return await original_run_in_thread(handler)

    monkeypatch.setattr(asset_db, "_run_in_thread", counting_run_in_thread)
    detail = await asset_db.get_outlook_account_detail_view("asset@example.com")

    assert calls == 1
    assert detail is not None
    assert detail["profile_cache"]["profile_json"]
    assert detail["security_methods_snapshot"][0]["method_id"] == "method-1"
    assert detail["recent_operations"][0]["operation"] == "profile.read"
    assert "access_token" not in detail["token"]
    assert "refresh_token" not in detail["token"]


@pytest.mark.asyncio
async def test_asset_indexes_are_created(asset_db):
    with closing(asset_db.get_connection()) as conn:
        indexes = {
            row["name"]
            for table in (
                "outlook_accounts",
                "oauth_tokens",
                "account_security_methods_snapshot",
                "account_operation_audit",
            )
            for row in conn.execute(f"PRAGMA index_list('{table}')").fetchall()
        }

    assert "idx_outlook_accounts_updated_email" in indexes
    assert "idx_outlook_accounts_status_updated_email" in indexes
    assert "idx_outlook_accounts_type_updated_email" in indexes
    assert "idx_oauth_tokens_email_status_id" in indexes
    assert "idx_account_security_snapshot_email_type_id" in indexes
    assert "idx_account_operation_audit_email_id" in indexes
    assert "idx_oauth_tokens_email_status" not in indexes


def test_public_token_projection_removes_credentials():
    public = to_public_oauth_token(
        {
            "id": 7,
            "oauth_config_id": 3,
            "email": "asset@example.com",
            "access_token": "access-secret",
            "refresh_token": "refresh-secret",
            "status": "active",
        }
    )

    assert public is not None
    assert public["has_access_token"] is True
    assert public["has_refresh_token"] is True
    assert "access_token" not in public
    assert "refresh_token" not in public
    assert "secret" not in repr(public)


@pytest.mark.asyncio
async def test_batch_refresh_deduplicates_and_preserves_input_order(monkeypatch):
    async def fake_refresh(email: str, *, channel_id=None):
        if email == "second@example.com":
            raise RuntimeError("refresh failed")
        return {"email": email, "expires_at": "2030-01-01T00:00:00+00:00"}

    refresh = AsyncMock(side_effect=fake_refresh)
    monkeypatch.setattr(graph_token_service, "refresh_account_token", refresh)

    summary = await graph_token_service.batch_refresh_account_tokens(
        emails=[
            " First@example.com ",
            "first@example.com",
            "second@example.com",
            "",
        ],
        concurrency=999,
    )

    assert summary["requested"] == 2
    assert summary["refreshed"] == 1
    assert summary["failed"] == 1
    assert [item["email"] for item in summary["details"]] == [
        "First@example.com",
        "second@example.com",
    ]
    assert refresh.await_count == 2


def test_batch_refresh_schema_enforces_resource_bounds():
    request = BatchRefreshRequest(limit=200, offset=0, concurrency=20)
    assert request.limit == 200
    assert request.concurrency == 20

    with pytest.raises(PydanticValidationError):
        BatchRefreshRequest(limit=201)
    with pytest.raises(PydanticValidationError):
        BatchRefreshRequest(offset=-1)
    with pytest.raises(PydanticValidationError):
        BatchRefreshRequest(concurrency=21)
    with pytest.raises(PydanticValidationError):
        BatchRefreshRequest(
            emails=[f"user-{index}@example.com" for index in range(201)]
        )
    with pytest.raises(PydanticValidationError):
        BatchRefreshRequest(emails=[f"{'a' * 310}@example.com"])
