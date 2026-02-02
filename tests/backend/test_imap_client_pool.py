"""
Tests for IMAPClientPool.

Tests cover:
- Client creation and caching
- LRU eviction policy
- Token change handling
- Connection cleanup
- Metrics collection
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


class TestIMAPClientPool:
    """Tests for IMAPClientPool class."""

    @pytest.fixture
    def imap_pool(self):
        """Create IMAPClientPool instance."""
        from app.services.imap_client_pool import IMAPClientPool
        return IMAPClientPool()

    @pytest.fixture
    def mock_imap_client(self):
        """Create a mock IMAP client."""
        client = MagicMock()
        client.close = AsyncMock()
        client.is_connected = True
        client.refresh_token = "test-token"
        return client

    @pytest.mark.asyncio
    async def test_get_or_create_creates_new_client(self, imap_pool):
        """Test that get_or_create creates a new client for unknown email."""
        account_info = {
            "email": "test@example.com",
            "password": "password",
            "client_id": "client-id",
            "refresh_token": "refresh-token",
        }

        with patch('app.services.imap_client_pool.IMAPEmailClient') as MockClient:
            mock_instance = MagicMock()
            mock_instance.refresh_token = "refresh-token"
            MockClient.return_value = mock_instance

            client = await imap_pool.get_or_create("test@example.com", account_info)

            assert client is not None
            MockClient.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_or_create_returns_cached_client(self, imap_pool, mock_imap_client):
        """Test that get_or_create returns cached client for known email."""
        # Pre-populate cache
        imap_pool._clients["test@example.com"] = mock_imap_client
        imap_pool._token_hashes["test@example.com"] = hash("test-token")

        account_info = {
            "email": "test@example.com",
            "refresh_token": "test-token",
        }

        client = await imap_pool.get_or_create("test@example.com", account_info)

        assert client is mock_imap_client

    @pytest.mark.asyncio
    async def test_get_or_create_replaces_on_token_change(self, imap_pool, mock_imap_client):
        """Test that client is replaced when token changes."""
        # Pre-populate cache with old token
        imap_pool._clients["test@example.com"] = mock_imap_client
        imap_pool._token_hashes["test@example.com"] = hash("old-token")

        account_info = {
            "email": "test@example.com",
            "password": "password",
            "client_id": "client-id",
            "refresh_token": "new-token",  # Different token
        }

        with patch('app.services.imap_client_pool.IMAPEmailClient') as MockClient:
            mock_new_instance = MagicMock()
            mock_new_instance.refresh_token = "new-token"
            MockClient.return_value = mock_new_instance

            client = await imap_pool.get_or_create("test@example.com", account_info)

            # Old client should be closed
            mock_imap_client.close.assert_called_once()
            # New client should be created
            MockClient.assert_called_once()

    @pytest.mark.asyncio
    async def test_remove_clears_client(self, imap_pool, mock_imap_client):
        """Test that remove clears client from pool."""
        imap_pool._clients["test@example.com"] = mock_imap_client
        imap_pool._token_hashes["test@example.com"] = hash("test-token")

        await imap_pool.remove("test@example.com")

        assert "test@example.com" not in imap_pool._clients
        assert "test@example.com" not in imap_pool._token_hashes
        mock_imap_client.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_remove_handles_nonexistent_email(self, imap_pool):
        """Test that remove handles non-existent email gracefully."""
        # Should not raise
        await imap_pool.remove("nonexistent@example.com")

    @pytest.mark.asyncio
    async def test_cleanup_all_closes_all_clients(self, imap_pool):
        """Test that cleanup_all closes all clients."""
        clients = []
        for i in range(3):
            client = MagicMock()
            client.close = AsyncMock()
            email = f"test{i}@example.com"
            imap_pool._clients[email] = client
            clients.append(client)

        await imap_pool.cleanup_all()

        assert len(imap_pool._clients) == 0
        for client in clients:
            client.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_lru_eviction(self, imap_pool):
        """Test that LRU eviction works when pool is full."""
        # Set a small max size for testing
        with patch.object(imap_pool, '_max_clients', 2):
            # Add clients
            for i in range(3):
                email = f"test{i}@example.com"
                account_info = {
                    "email": email,
                    "password": "password",
                    "client_id": "client-id",
                    "refresh_token": f"token-{i}",
                }
                
                with patch('app.services.imap_client_pool.IMAPEmailClient') as MockClient:
                    mock_instance = MagicMock()
                    mock_instance.refresh_token = f"token-{i}"
                    mock_instance.close = AsyncMock()
                    MockClient.return_value = mock_instance
                    
                    await imap_pool.get_or_create(email, account_info)

            # Pool should have at most 2 clients due to eviction
            assert len(imap_pool._clients) <= 2

    def test_get_metrics_returns_stats(self, imap_pool, mock_imap_client):
        """Test that get_metrics returns pool statistics."""
        imap_pool._clients["test@example.com"] = mock_imap_client

        metrics = imap_pool.get_metrics()

        assert "active_clients" in metrics
        assert metrics["active_clients"] == 1


class TestIMAPClientPoolConcurrency:
    """Concurrency tests for IMAPClientPool."""

    @pytest.mark.asyncio
    async def test_concurrent_get_or_create_same_email(self):
        """Test concurrent get_or_create for same email."""
        from app.services.imap_client_pool import IMAPClientPool
        
        pool = IMAPClientPool()
        creation_count = 0

        async def mock_create(*args, **kwargs):
            nonlocal creation_count
            creation_count += 1
            await asyncio.sleep(0.1)
            client = MagicMock()
            client.refresh_token = "token"
            return client

        account_info = {
            "email": "test@example.com",
            "password": "password",
            "client_id": "client-id",
            "refresh_token": "token",
        }

        with patch('app.services.imap_client_pool.IMAPEmailClient', mock_create):
            tasks = [
                pool.get_or_create("test@example.com", account_info)
                for _ in range(5)
            ]
            results = await asyncio.gather(*tasks, return_exceptions=True)

        # All results should be valid (not exceptions)
        valid_results = [r for r in results if not isinstance(r, Exception)]
        assert len(valid_results) > 0
