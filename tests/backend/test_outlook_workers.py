from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from app.workers import protocol_tasks


def test_protocol_bind_secondary_timeout_marks_failed_and_rotates(monkeypatch):
    monkeypatch.setattr(
        protocol_tasks.db_manager,
        "get_protocol_task",
        AsyncMock(return_value={"id": 1, "task_type": "bind", "resource_id": 11, "retry_count": 0}),
    )
    monkeypatch.setattr(protocol_tasks, "_run_protocol_bind", AsyncMock(side_effect=TimeoutError("code timeout")))
    monkeypatch.setattr(
        protocol_tasks,
        "_maybe_rotate_resource",
        AsyncMock(return_value={"replacement": {"id": 99}}),
    )
    monkeypatch.setattr(protocol_tasks, "update_task_status", AsyncMock(return_value=None))
    monkeypatch.setattr(protocol_tasks, "_fail_step", AsyncMock(return_value=None))
    monkeypatch.setattr(protocol_tasks.db_manager, "update_protocol_task", AsyncMock(return_value=True))

    with pytest.raises(TimeoutError):
        protocol_tasks.protocol_bind_secondary.run(1)

    protocol_tasks.update_task_status.assert_awaited()
    protocol_tasks.db_manager.update_protocol_task.assert_awaited()


def test_protocol_rebind_secondary_preserves_needs_manual(monkeypatch):
    task = {"id": 2, "task_type": "rebind", "resource_id": 12, "retry_count": 0}
    monkeypatch.setattr(protocol_tasks.db_manager, "get_protocol_task", AsyncMock(side_effect=[task, {"status": "needs_manual"}]))
    monkeypatch.setattr(protocol_tasks, "_run_protocol_rebind", AsyncMock(side_effect=RuntimeError("boom")))
    monkeypatch.setattr(protocol_tasks, "update_task_status", AsyncMock(return_value=None))
    monkeypatch.setattr(protocol_tasks, "_fail_step", AsyncMock(return_value=None))

    with pytest.raises(RuntimeError):
        protocol_tasks.protocol_rebind_secondary.run(2)

    protocol_tasks.update_task_status.assert_not_awaited()
    protocol_tasks._fail_step.assert_awaited()


def test_protocol_bind_secondary_uses_browser_fallback(monkeypatch):
    task = {"id": 10, "task_type": "bind", "resource_id": 11, "retry_count": 0}
    monkeypatch.setattr(protocol_tasks.db_manager, "get_protocol_task", AsyncMock(return_value=task))
    monkeypatch.setattr(protocol_tasks, "_run_protocol_bind", AsyncMock(side_effect=RuntimeError("captcha")))
    monkeypatch.setattr(protocol_tasks, "_browser_fallback_enabled", lambda: True)
    monkeypatch.setattr(
        protocol_tasks,
        "_run_browser_bind_fallback",
        AsyncMock(return_value={"mode": "bind", "fallback": "browser"}),
    )

    result = protocol_tasks.protocol_bind_secondary.run(10)

    assert result["fallback"] == "browser"
    protocol_tasks._run_browser_bind_fallback.assert_awaited_once_with(10, task)


def test_protocol_rebind_secondary_uses_browser_fallback(monkeypatch):
    task = {"id": 11, "task_type": "rebind", "resource_id": 12, "retry_count": 0}
    monkeypatch.setattr(
        protocol_tasks.db_manager,
        "get_protocol_task",
        AsyncMock(side_effect=[task, {"status": "needs_manual"}]),
    )
    monkeypatch.setattr(protocol_tasks, "_run_protocol_rebind", AsyncMock(side_effect=RuntimeError("captcha")))
    monkeypatch.setattr(protocol_tasks, "_browser_fallback_enabled", lambda: True)
    monkeypatch.setattr(
        protocol_tasks,
        "_run_browser_rebind_fallback",
        AsyncMock(return_value={"mode": "rebind", "fallback": "browser"}),
    )

    result = protocol_tasks.protocol_rebind_secondary.run(11)

    assert result["fallback"] == "browser"
    protocol_tasks._run_browser_rebind_fallback.assert_awaited_once_with(11, task)


@pytest.mark.asyncio
async def test_build_code_provider_enters_waiting_code(monkeypatch):
    monkeypatch.setattr(protocol_tasks, "update_task_status", AsyncMock(return_value=None))
    monkeypatch.setattr(protocol_tasks, "publish_task_event", lambda *args, **kwargs: True)
    monkeypatch.setattr(protocol_tasks, "add_task_step", AsyncMock(return_value=1))

    provider = await protocol_tasks._build_code_provider(10, {"address": "a@example.com", "notes": '{"static_code":"123456"}'})
    result = await provider.fetch_code("a@example.com")

    assert result.code == "123456"
    protocol_tasks.update_task_status.assert_awaited_with(10, "waiting_code")


@pytest.mark.asyncio
async def test_rollback_rebind_restores_old_resource(monkeypatch):
    monkeypatch.setattr(
        protocol_tasks.db_manager,
        "get_aux_email_resource_by_address",
        AsyncMock(return_value={"id": 5, "address": "old@example.com"}),
    )
    monkeypatch.setattr(protocol_tasks.db_manager, "update_aux_email_resource", AsyncMock(return_value=True))
    monkeypatch.setattr(protocol_tasks, "_mark_resource_available", AsyncMock(return_value=None))

    result = await protocol_tasks._rollback_rebind(
        {"target_email": "user@example.com", "old_email": "old@example.com"},
        {"id": 8, "address": "new@example.com"},
    )

    assert result["rolled_back"] is True
    protocol_tasks._mark_resource_available.assert_awaited_with(8)
