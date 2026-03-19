"""Helpers for protocol task lifecycle and step persistence."""

from __future__ import annotations

from typing import Any

from ...db import db_manager


async def update_task_status(
    task_id: int,
    status: str,
    *,
    error_message: str = "",
    retry_count: int | None = None,
) -> None:
    payload: dict[str, Any] = {"status": status}
    if error_message:
        payload["error_message"] = error_message
    if retry_count is not None:
        payload["retry_count"] = retry_count
    await db_manager.update_protocol_task(task_id, **payload)


async def add_task_step(
    task_id: int,
    step: str,
    *,
    status: str = "pending",
    detail: str = "",
    started_at: str | None = None,
    finished_at: str | None = None,
) -> int:
    return await db_manager.add_protocol_task_step(
        task_id,
        step,
        status=status,
        detail=detail,
        started_at=started_at,
        finished_at=finished_at,
    )
