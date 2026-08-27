"""Tests for SQLite connection and executor lifecycle management."""

import asyncio
from pathlib import Path

import pytest
from app.db.connection import DEFAULT_SQLITE_BUSY_TIMEOUT_MS, ConnectionMixin
from app.db.manager import DatabaseManager


class _ConnectionHarness(ConnectionMixin):
    pass


@pytest.mark.asyncio
async def test_database_executor_is_lazy_and_recreatable(tmp_path):
    harness = _ConnectionHarness()
    harness._init_connection("lazy.db", Path(tmp_path))

    assert harness._executor is None
    result = await harness._run_in_thread(
        lambda conn: int(conn.execute("SELECT 1").fetchone()[0])
    )
    assert result == 1
    assert harness._executor is not None

    await asyncio.to_thread(harness.close)
    assert harness._executor is None

    result = await harness._run_in_thread(
        lambda conn: int(conn.execute("SELECT 2").fetchone()[0])
    )
    assert result == 2
    await asyncio.to_thread(harness.close)


def test_connections_enable_busy_timeout(tmp_path):
    harness = _ConnectionHarness()
    harness._init_connection("busy.db", Path(tmp_path))
    try:
        with harness.get_connection() as conn:
            busy_timeout = int(conn.execute("PRAGMA busy_timeout").fetchone()[0])
        assert busy_timeout == DEFAULT_SQLITE_BUSY_TIMEOUT_MS
    finally:
        harness.close()


def test_database_manager_initializes_wal_once(tmp_path):
    manager = DatabaseManager(str(tmp_path / "wal.db"))
    try:
        with manager.get_connection() as conn:
            journal_mode = str(conn.execute("PRAGMA journal_mode").fetchone()[0])
        assert journal_mode.lower() == "wal"
    finally:
        manager.close()
