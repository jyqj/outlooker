"""Tests for background token refresh shutdown semantics."""

import asyncio

import pytest

from app.services import token_refresh_service


@pytest.mark.asyncio
async def test_stop_background_refresh_cancels_and_awaits_task(monkeypatch):
    started = asyncio.Event()

    async def worker() -> None:
        started.set()
        await asyncio.Event().wait()

    task = asyncio.create_task(worker())
    await started.wait()
    monkeypatch.setattr(token_refresh_service, "_task", task)

    await token_refresh_service.stop_background_refresh()

    assert task.done()
    assert token_refresh_service._task is None


@pytest.mark.asyncio
async def test_stop_background_refresh_is_idempotent(monkeypatch):
    monkeypatch.setattr(token_refresh_service, "_task", None)
    await token_refresh_service.stop_background_refresh()
    assert token_refresh_service._task is None
