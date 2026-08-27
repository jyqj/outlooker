"""Regression tests for the IMAP-to-SQLite cache hot path."""

from unittest.mock import AsyncMock, patch

import pytest
from app.imap_client import IMAPEmailClient


@pytest.mark.asyncio
async def test_imap_client_persists_messages_with_one_batch_call():
    client = IMAPEmailClient(
        "batch@example.com",
        {"refresh_token": "refresh-token"},
    )
    messages = [
        {"id": "1", "subject": "One"},
        {"id": "2", "subject": "Two"},
    ]

    with patch(
        "app.imap_client.db_manager.cache_emails",
        new_callable=AsyncMock,
        return_value=2,
    ) as cache_emails:
        await client._cache_messages("INBOX", messages)

    cache_emails.assert_awaited_once_with(
        "batch@example.com",
        messages,
        folder="INBOX",
    )
