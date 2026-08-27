#!/usr/bin/env python3
"""
Database connection management module.

Handles SQLite connection creation, thread pool execution, and resource management.
"""

import asyncio
import logging
import sqlite3
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
from pathlib import Path
from typing import TypeVar

logger = logging.getLogger(__name__)

T = TypeVar("T")
DEFAULT_SQLITE_BUSY_TIMEOUT_MS = 5_000


class ConnectionMixin:
    """Mixin providing database connection management functionality."""

    db_path: str
    _executor: ThreadPoolExecutor | None
    _db_thread_pool_size: int
    _sqlite_busy_timeout_ms: int

    def _init_connection(self, db_path: str, project_root: Path) -> None:
        """Initialize connection settings without eagerly creating worker threads."""
        resolved = Path(db_path)
        if not resolved.is_absolute():
            resolved = project_root / resolved
        resolved.parent.mkdir(parents=True, exist_ok=True)
        self.db_path = str(resolved)

        # Delay the executor until the first asynchronous database operation. This
        # avoids creating idle threads for CLI/import-only processes and test collection.
        from ..settings import get_settings

        self._db_thread_pool_size = max(1, int(get_settings().db_thread_pool_size))
        self._sqlite_busy_timeout_ms = DEFAULT_SQLITE_BUSY_TIMEOUT_MS
        self._executor = None

    def _configure_connection(self, conn: sqlite3.Connection) -> None:
        """Apply per-connection SQLite settings."""
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA synchronous = NORMAL")
        conn.execute("PRAGMA foreign_keys = ON")
        conn.execute(f"PRAGMA busy_timeout = {self._sqlite_busy_timeout_ms}")

    def _initialize_database_pragmas(self, conn: sqlite3.Connection) -> None:
        """Apply persistent database settings once during schema initialization."""
        conn.execute("PRAGMA journal_mode = WAL")
        self._configure_connection(conn)

    def _create_connection(self) -> sqlite3.Connection:
        """Create a new SQLite connection with row factory and lock backoff enabled."""
        conn = sqlite3.connect(
            self.db_path,
            check_same_thread=False,
            timeout=self._sqlite_busy_timeout_ms / 1_000,
        )
        self._configure_connection(conn)
        return conn

    def get_connection(self) -> sqlite3.Connection:
        """
        Get a synchronous connection for legacy code compatibility.

        Caller is responsible for closing the connection.
        """
        return self._create_connection()

    def _get_executor(self) -> ThreadPoolExecutor:
        """Get or lazily create the database thread pool executor."""
        if self._executor is None:
            self._executor = ThreadPoolExecutor(
                max_workers=self._db_thread_pool_size,
                thread_name_prefix="db-worker",
            )
        return self._executor

    async def _run_in_thread(self, handler: Callable[[sqlite3.Connection], T]) -> T:
        """Run a database operation in the dedicated thread pool."""

        def _runner() -> T:
            with closing(self._create_connection()) as conn:
                return handler(conn)

        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(self._get_executor(), _runner)

    def close(self) -> None:
        """Shut down the internal thread pool; per-operation connections close themselves."""
        executor, self._executor = self._executor, None
        if executor is not None:
            executor.shutdown(wait=True, cancel_futures=True)
