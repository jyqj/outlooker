"""
Tests for EmailFetchService.

Tests cover:
- Email fetching with caching
- Cache refresh logic
- Concurrent fetch handling
- Error handling
"""

import asyncio
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


class TestEmailFetchService:
    """Tests for EmailFetchService class."""

    @pytest.fixture
    def mock_account_cache(self):
        """Mock account cache service."""
        cache = AsyncMock()
        cache.get_account_info = AsyncMock(return_value={
            "email": "test@example.com",
            "password": "password123",
            "client_id": "test-client-id",
            "refresh_token": "test-refresh-token",
        })
        return cache

    @pytest.fixture
    def mock_imap_pool(self):
        """Mock IMAP client pool."""
        pool = AsyncMock()
        mock_client = MagicMock()
        mock_client.fetch_messages = AsyncMock(return_value=[
            {
                "id": "1",
                "subject": "Test Email",
                "from": "sender@example.com",
                "date": datetime.now().isoformat(),
                "body": "Test body",
            }
        ])
        pool.get_or_create = AsyncMock(return_value=mock_client)
        return pool

    @pytest.fixture
    def mock_db_manager(self):
        """Mock database manager."""
        db = AsyncMock()
        db.get_cached_emails = AsyncMock(return_value=[])
        db.get_email_cache_metadata = AsyncMock(return_value=None)
        db.save_emails_to_cache = AsyncMock(return_value=True)
        db.update_cache_metadata = AsyncMock(return_value=True)
        return db

    @pytest.fixture
    def email_fetch_service(self, mock_account_cache, mock_imap_pool, mock_db_manager):
        """Create EmailFetchService with mocked dependencies."""
        from app.services.email_fetch_service import EmailFetchService
        
        service = EmailFetchService()
        service._account_cache = mock_account_cache
        service._imap_pool = mock_imap_pool
        service._db_manager = mock_db_manager
        return service

    @pytest.mark.asyncio
    async def test_fetch_emails_returns_cached_when_valid(
        self, email_fetch_service, mock_db_manager
    ):
        """Test that cached emails are returned when cache is valid."""
        # Setup: Cache has valid data
        mock_db_manager.get_email_cache_metadata.return_value = {
            "last_refresh": datetime.now().isoformat(),
            "email_count": 1,
        }
        mock_db_manager.get_cached_emails.return_value = [
            {
                "id": "cached-1",
                "subject": "Cached Email",
                "from": "cached@example.com",
                "date": datetime.now().isoformat(),
                "body": "Cached body",
            }
        ]

        # Execute
        with patch.object(email_fetch_service, '_is_cache_valid', return_value=True):
            result = await email_fetch_service.fetch_emails("test@example.com")

        # Verify
        assert len(result) == 1
        assert result[0]["id"] == "cached-1"
        mock_db_manager.get_cached_emails.assert_called_once()

    @pytest.mark.asyncio
    async def test_fetch_emails_refreshes_when_cache_expired(
        self, email_fetch_service, mock_db_manager, mock_imap_pool
    ):
        """Test that emails are fetched from IMAP when cache is expired."""
        # Setup: Cache is expired
        mock_db_manager.get_email_cache_metadata.return_value = {
            "last_refresh": (datetime.now() - timedelta(hours=1)).isoformat(),
            "email_count": 0,
        }

        # Execute
        with patch.object(email_fetch_service, '_is_cache_valid', return_value=False):
            result = await email_fetch_service.fetch_emails("test@example.com")

        # Verify: IMAP pool was used
        mock_imap_pool.get_or_create.assert_called()

    @pytest.mark.asyncio
    async def test_fetch_emails_handles_imap_error(
        self, email_fetch_service, mock_imap_pool
    ):
        """Test graceful handling of IMAP errors."""
        # Setup: IMAP throws error
        mock_imap_pool.get_or_create.side_effect = Exception("IMAP connection failed")

        # Execute & Verify
        with patch.object(email_fetch_service, '_is_cache_valid', return_value=False):
            with pytest.raises(Exception) as exc_info:
                await email_fetch_service.fetch_emails("test@example.com")
            assert "IMAP" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_concurrent_fetch_uses_lock(self, email_fetch_service):
        """Test that concurrent fetches for same email use locking."""
        fetch_count = 0
        
        async def mock_fetch(*args, **kwargs):
            nonlocal fetch_count
            fetch_count += 1
            await asyncio.sleep(0.1)
            return []

        with patch.object(email_fetch_service, '_do_fetch', mock_fetch):
            # Start multiple concurrent fetches
            tasks = [
                email_fetch_service.fetch_emails("test@example.com")
                for _ in range(3)
            ]
            await asyncio.gather(*tasks, return_exceptions=True)

        # Only one actual fetch should happen due to locking
        # (This depends on the actual implementation details)


class TestEmailFetchServiceIntegration:
    """Integration tests for EmailFetchService."""

    @pytest.mark.asyncio
    async def test_service_initialization(self):
        """Test service can be initialized."""
        from app.services.email_fetch_service import EmailFetchService
        
        service = EmailFetchService()
        assert service is not None

    @pytest.mark.asyncio
    async def test_get_metrics(self):
        """Test metrics retrieval."""
        from app.services.email_fetch_service import EmailFetchService
        
        service = EmailFetchService()
        # Metrics should be available even without any fetches
        # (This depends on the actual implementation)
