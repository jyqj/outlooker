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


class ConnectionMixin:
    """Mixin providing database connection management functionality."""

    db_path: str
    _executor: ThreadPoolExecutor | None
    _executor_loop: asyncio.AbstractEventLoop | None

    def _init_connection(self, db_path: str, project_root: Path) -> None:
        """Initialize connection settings."""
        resolved = Path(db_path)
        if not resolved.is_absolute():
            resolved = project_root / resolved
        resolved.parent.mkdir(parents=True, exist_ok=True)
        self.db_path = str(resolved)
        # 延迟导入避免循环依赖
        from ..settings import get_settings
        pool_size = get_settings().db_thread_pool_size
        self._executor: ThreadPoolExecutor | None = ThreadPoolExecutor(
            max_workers=pool_size, thread_name_prefix="db-worker"
        )
        self._executor_loop: asyncio.AbstractEventLoop | None = None

    def _create_connection(self) -> sqlite3.Connection:
        """Create a new SQLite connection with row factory enabled."""
        conn = sqlite3.connect(self.db_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    def get_connection(self) -> sqlite3.Connection:
        """
        Get a synchronous connection for legacy code compatibility.
        
        Caller is responsible for closing the connection.
        """
        return self._create_connection()

    def _get_executor(self) -> ThreadPoolExecutor:
        """Get the database thread pool executor."""
        if self._executor is None:
            # 延迟导入避免循环依赖
            from ..settings import get_settings
            pool_size = get_settings().db_thread_pool_size
            self._executor = ThreadPoolExecutor(max_workers=pool_size, thread_name_prefix="db-worker")
        return self._executor

    async def _run_in_thread(self, handler: Callable[[sqlite3.Connection], T]) -> T:
        """
        Run a database operation in the background thread pool.
        
        Ensures the connection is properly released after the operation.
        """

        def _runner() -> T:
            with closing(self._create_connection()) as conn:
                return handler(conn)

        loop = asyncio.get_running_loop()
        executor = self._get_executor()
        return await loop.run_in_executor(executor, _runner)

    def close(self) -> None:
        """
        Close resources associated with the database manager.

        Primarily shuts down the internal thread pool executor.
        Actual SQLite connections are closed per-operation.
        """
        if self._executor is not None:
            self._executor.shutdown(wait=True)
            self._executor = None
            self._executor_loop = None
