"""
Tests for CacheWarmupService.

Tests cover:
- Background warmup task management
- Concurrent warmup limiting
- Error handling and recovery
- Statistics tracking
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


class TestCacheWarmupService:
    """Tests for CacheWarmupService class."""

    @pytest.fixture
    def cache_warmup_service(self):
        """Create CacheWarmupService instance."""
        from app.services.cache_warmup_service import CacheWarmupService
        return CacheWarmupService()

    @pytest.fixture
    def mock_email_fetch_service(self):
        """Mock email fetch service."""
        service = AsyncMock()
        service.fetch_emails = AsyncMock(return_value=[])
        return service

    @pytest.mark.asyncio
    async def test_warmup_account_success(self, cache_warmup_service):
        """Test successful account warmup."""
        with patch('app.services.cache_warmup_service.email_fetch_service') as mock_service:
            mock_service.fetch_emails = AsyncMock(return_value=[
                {"id": "1", "subject": "Test"}
            ])

            result = await cache_warmup_service._warmup_account("test@example.com")

            assert result is True
            mock_service.fetch_emails.assert_called_once()

    @pytest.mark.asyncio
    async def test_warmup_account_handles_error(self, cache_warmup_service):
        """Test that warmup handles errors gracefully."""
        with patch('app.services.cache_warmup_service.email_fetch_service') as mock_service:
            mock_service.fetch_emails = AsyncMock(side_effect=Exception("Fetch failed"))

            result = await cache_warmup_service._warmup_account("test@example.com")

            # Should return False on error, not raise
            assert result is False

    @pytest.mark.asyncio
    async def test_warmup_accounts_batch(self, cache_warmup_service):
        """Test batch warmup of multiple accounts."""
        emails = ["test1@example.com", "test2@example.com", "test3@example.com"]

        with patch('app.services.cache_warmup_service.email_fetch_service') as mock_service:
            mock_service.fetch_emails = AsyncMock(return_value=[])

            results = await cache_warmup_service.warmup_accounts(emails)

            assert "success_count" in results
            assert "failure_count" in results
            assert results["success_count"] + results["failure_count"] == len(emails)

    @pytest.mark.asyncio
    async def test_warmup_respects_concurrency_limit(self, cache_warmup_service):
        """Test that warmup respects concurrency limit."""
        concurrent_count = 0
        max_concurrent = 0

        async def mock_fetch(*args, **kwargs):
            nonlocal concurrent_count, max_concurrent
            concurrent_count += 1
            max_concurrent = max(max_concurrent, concurrent_count)
            await asyncio.sleep(0.1)
            concurrent_count -= 1
            return []

        emails = [f"test{i}@example.com" for i in range(10)]

        with patch('app.services.cache_warmup_service.email_fetch_service') as mock_service:
            mock_service.fetch_emails = mock_fetch
            # Set a low concurrency limit
            cache_warmup_service._semaphore = asyncio.Semaphore(3)

            await cache_warmup_service.warmup_accounts(emails)

            # Max concurrent should not exceed semaphore limit
            assert max_concurrent <= 3

    @pytest.mark.asyncio
    async def test_start_background_warmup(self, cache_warmup_service):
        """Test starting background warmup task."""
        emails = ["test@example.com"]

        with patch.object(cache_warmup_service, 'warmup_accounts', new_callable=AsyncMock) as mock_warmup:
            mock_warmup.return_value = {"success_count": 1, "failure_count": 0}

            task = await cache_warmup_service.start_background_warmup(emails)

            # Task should be created
            assert task is not None

            # Wait for task to complete
            await asyncio.sleep(0.1)

    @pytest.mark.asyncio
    async def test_cleanup_cancels_running_tasks(self, cache_warmup_service):
        """Test that cleanup cancels running tasks."""
        # Start a long-running task
        async def long_task():
            await asyncio.sleep(10)

        task = asyncio.create_task(long_task())
        cache_warmup_service._running_tasks.add(task)

        await cache_warmup_service.cleanup()

        # Task should be cancelled
        assert task.cancelled() or task.done()
        assert len(cache_warmup_service._running_tasks) == 0

    def test_get_stats(self, cache_warmup_service):
        """Test getting warmup statistics."""
        stats = cache_warmup_service.get_stats()

        assert "running_tasks" in stats
        assert "total_warmups" in stats or isinstance(stats, dict)


class TestCacheWarmupServiceErrors:
    """Error handling tests for CacheWarmupService."""

    @pytest.mark.asyncio
    async def test_warmup_continues_on_individual_failure(self):
        """Test that batch warmup continues when individual account fails."""
        from app.services.cache_warmup_service import CacheWarmupService
        
        service = CacheWarmupService()
        emails = ["good@example.com", "bad@example.com", "good2@example.com"]
        call_count = 0

        async def mock_fetch(email, *args, **kwargs):
            nonlocal call_count
            call_count += 1
            if "bad" in email:
                raise Exception("Fetch failed")
            return []

        with patch('app.services.cache_warmup_service.email_fetch_service') as mock_service:
            mock_service.fetch_emails = mock_fetch

            results = await service.warmup_accounts(emails)

            # All emails should be attempted
            assert call_count == 3
            assert results["failure_count"] >= 1

    @pytest.mark.asyncio
    async def test_cleanup_handles_task_errors(self):
        """Test that cleanup handles task errors gracefully."""
        from app.services.cache_warmup_service import CacheWarmupService
        
        service = CacheWarmupService()

        async def error_task():
            raise Exception("Task error")

        task = asyncio.create_task(error_task())
        service._running_tasks.add(task)

        # Wait for task to fail
        await asyncio.sleep(0.1)

        # Cleanup should not raise
        await service.cleanup()
