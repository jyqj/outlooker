#!/usr/bin/env python3
"""
Shared base typing helpers for database mixins.

The database layer uses a mixin-based design where operational mixins rely on
`ConnectionMixin._run_in_thread`. Mypy analyzes each mixin in isolation, so we
provide a small base class to declare the expected interface.
"""

import sqlite3
from collections.abc import Callable
from typing import TypeVar

T = TypeVar("T")


class RunInThreadMixin:
    async def _run_in_thread(self, handler: Callable[[sqlite3.Connection], T]) -> T:
        raise NotImplementedError
