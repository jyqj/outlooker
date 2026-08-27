"""Tests for batched email cache writes."""

import asyncio

import pytest
import pytest_asyncio

from app.db.manager import DatabaseManager


def _message(message_id: str, subject: str | None = None) -> dict:
    return {
        "id": message_id,
        "subject": subject or f"Subject {message_id}",
        "from": {
            "emailAddress": {
                "name": "Sender",
                "address": "sender@example.com",
            }
        },
        "receivedDateTime": f"2026-01-01T00:00:{int(message_id):02d}Z",
        "bodyPreview": f"Preview {message_id}",
        "body": {"content": f"Body {message_id}", "contentType": "text"},
    }


@pytest_asyncio.fixture
async def database(tmp_path):
    manager = DatabaseManager(str(tmp_path / "email-cache.db"))
    try:
        yield manager
    finally:
        await asyncio.to_thread(manager.close)


@pytest.mark.asyncio
async def test_cache_emails_upserts_a_batch_in_one_public_call(database):
    cached = await database.cache_emails(
        "batch@example.com",
        [_message("1"), _message("2"), _message("3")],
    )

    assert cached == 3
    messages = await database.get_cached_messages("batch@example.com", limit=10)
    assert [message["id"] for message in messages] == ["3", "2", "1"]
    assert messages[0]["from"]["emailAddress"]["address"] == "sender@example.com"

    updated = await database.cache_emails(
        "batch@example.com",
        [_message("2", subject="Updated subject")],
    )

    assert updated == 1
    message = await database.get_cached_email("batch@example.com", "2")
    assert message is not None
    assert message["subject"] == "Updated subject"


@pytest.mark.asyncio
async def test_cache_emails_enforces_capacity_after_the_batch(database, monkeypatch):
    monkeypatch.setattr(
        "app.db.email_cache.settings.email_cache_limit_per_account",
        2,
    )

    cached = await database.cache_emails(
        "limit@example.com",
        [_message("1"), _message("2"), _message("3")],
    )

    assert cached == 3
    messages = await database.get_cached_messages("limit@example.com", limit=10)
    assert [message["id"] for message in messages] == ["3", "2"]


@pytest.mark.asyncio
async def test_cache_email_keeps_the_single_message_contract(database):
    result = await database.cache_email(
        "single@example.com",
        "7",
        _message("7", subject="Single"),
    )

    assert result is True
    message = await database.get_cached_email("single@example.com", "7")
    assert message is not None
    assert message["subject"] == "Single"
