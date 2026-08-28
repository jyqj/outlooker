from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock

from app.services import system_config_service


def test_system_config_lock_rebinds_across_event_loops(monkeypatch):
    """Sequential embedded event loops must not reuse a loop-bound lock."""
    monkeypatch.setattr(
        system_config_service.db_manager,
        "get_system_config",
        AsyncMock(return_value=None),
    )
    monkeypatch.setattr(
        system_config_service.db_manager,
        "set_system_config",
        AsyncMock(return_value=True),
    )
    monkeypatch.setattr(system_config_service, "_read_system_config_file", lambda: {})

    async def load_with_lock_identity():
        config = await system_config_service.load_system_config()
        return config, id(system_config_service._get_system_config_lock())

    first_config, first_lock = asyncio.run(load_with_lock_identity())
    second_config, second_lock = asyncio.run(load_with_lock_identity())

    assert first_config == second_config
    assert first_lock != second_lock
