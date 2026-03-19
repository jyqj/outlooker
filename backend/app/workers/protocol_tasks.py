"""Celery tasks for Outlook protocol binding workflows."""

from __future__ import annotations

import asyncio
import json
import time
from datetime import UTC, datetime
from typing import Any

from ..core.metrics import record_protocol_task_metrics
from ..db import db_manager
from ..services.channeling.resource_pool_service import rotate_aux_email_resource
from ..services.outlook.protocol import OutlookProtocolError, build_protocol_client_for_channel
from ..services.outlook.protocol_code_provider import CallbackCodeProvider, CodeFetchResult
from ..services.tasks.progress_event_service import publish_task_event
from ..services.tasks.protocol_task_service import add_task_step, update_task_status
from .celery_app import celery_app


def _step_time() -> str:
    return datetime.now(UTC).isoformat()


async def _emit_step(task_id: int, step: str, detail: dict[str, Any] | None = None) -> None:
    await add_task_step(task_id, step, status="running", detail=json.dumps(detail or {}, ensure_ascii=False), started_at=_step_time())
    publish_task_event(task_id, step, detail)


async def _complete_step(task_id: int, step: str, detail: dict[str, Any] | None = None) -> None:
    await add_task_step(task_id, step, status="success", detail=json.dumps(detail or {}, ensure_ascii=False), finished_at=_step_time())
    publish_task_event(task_id, f"{step}:success", detail)


async def _fail_step(task_id: int, step: str, detail: dict[str, Any] | None = None) -> None:
    await add_task_step(task_id, step, status="failed", detail=json.dumps(detail or {}, ensure_ascii=False), finished_at=_step_time())
    publish_task_event(task_id, f"{step}:failed", detail)


async def _resolve_login_credentials(task: dict[str, Any]) -> tuple[str, str]:
    account = await db_manager.get_account(task["target_email"])
    if account:
        return task["target_email"], account.get("password", "")

    outlook_account = await db_manager.get_outlook_account(task["target_email"])
    if outlook_account and outlook_account.get("source_account_email"):
        source_email = outlook_account["source_account_email"]
        source_account = await db_manager.get_account(source_email)
        if source_account:
            return source_email, source_account.get("password", "")

    raise RuntimeError("Unable to resolve login credentials")


def _notes_json(resource: dict[str, Any]) -> dict[str, Any]:
    raw = resource.get("notes") or ""
    if not raw:
        return {}
    try:
        return json.loads(raw)
    except Exception:
        return {}


async def _build_code_provider(task_id: int, resource: dict[str, Any]) -> CallbackCodeProvider:
    async def _callback(**kwargs) -> CodeFetchResult:
        await update_task_status(task_id, "waiting_code")
        publish_task_event(task_id, "waiting_code", {"resource": resource["address"]})
        await add_task_step(
            task_id,
            "waiting_code",
            status="running",
            detail=json.dumps({"resource": resource["address"]}, ensure_ascii=False),
            started_at=_step_time(),
        )
        notes = _notes_json(resource)
        code = notes.get("static_code")
        if not code:
            raise TimeoutError("No verification code provider configured for resource")
        return CodeFetchResult(
            code=str(code),
            email_id=kwargs.get("min_email_id"),
            source="resource_notes",
        )

    return CallbackCodeProvider(_callback)


async def _mark_resource_bound(resource_id: int, target_email: str) -> None:
    await db_manager.update_aux_email_resource(
        resource_id,
        status="bound",
        bound_account_email=target_email,
        fail_count=0,
    )


async def _mark_resource_available(resource_id: int) -> None:
    await db_manager.update_aux_email_resource(
        resource_id,
        status="available",
        bound_account_email="",
    )


async def _run_protocol_bind(task_id: int) -> dict[str, Any]:
    task = await db_manager.get_protocol_task(task_id)
    if not task:
        raise RuntimeError("Protocol task not found")
    resource = await db_manager.get_aux_email_resource_by_id(int(task["resource_id"]))
    if not resource:
        raise RuntimeError("Auxiliary email resource not found")

    login_email, password = await _resolve_login_credentials(task)
    provider = await _build_code_provider(task_id, resource)

    await update_task_status(task_id, "running")
    await _emit_step(task_id, "login", {"email": login_email})

    async with await build_protocol_client_for_channel(task.get("channel_id")) as client:
        await client.login(login_email, password)
        await _complete_step(task_id, "login", {"email": login_email})

        if task.get("verification_email"):
            await _emit_step(task_id, "verify_identity", {"verification_email": task["verification_email"]})
            await client.verify_identity(task["verification_email"], provider)
            await _complete_step(task_id, "verify_identity", {"verification_email": task["verification_email"]})

        await _emit_step(task_id, "bind_recovery_email", {"recovery_email": resource["address"]})
        bind_result = await client.add_recovery_email(resource["address"], provider)
        await _complete_step(task_id, "bind_recovery_email", {"recovery_email": resource["address"]})

    await _mark_resource_bound(int(resource["id"]), task["target_email"])
    await update_task_status(task_id, "success")
    publish_task_event(task_id, "success", {"resource": resource["address"]})
    return bind_result


async def _rollback_rebind(task: dict[str, Any], new_resource: dict[str, Any]) -> dict[str, Any]:
    old_resource = await db_manager.get_aux_email_resource_by_address(task.get("old_email", ""))
    if old_resource:
        await db_manager.update_aux_email_resource(
            int(old_resource["id"]),
            status="bound",
            bound_account_email=task["target_email"],
        )
    await _mark_resource_available(int(new_resource["id"]))
    return {
        "rolled_back": True,
        "restored_old_resource": bool(old_resource),
        "released_new_resource": True,
    }


async def _run_protocol_rebind(task_id: int) -> dict[str, Any]:
    task = await db_manager.get_protocol_task(task_id)
    if not task:
        raise RuntimeError("Protocol task not found")
    resource = await db_manager.get_aux_email_resource_by_id(int(task["resource_id"]))
    if not resource:
        raise RuntimeError("New auxiliary email resource not found")

    login_email, password = await _resolve_login_credentials(task)
    provider = await _build_code_provider(task_id, resource)

    await update_task_status(task_id, "running")
    await _emit_step(task_id, "login", {"email": login_email})

    try:
        async with await build_protocol_client_for_channel(task.get("channel_id")) as client:
            await client.login(login_email, password)
            await _complete_step(task_id, "login", {"email": login_email})

            await _emit_step(task_id, "replace_recovery_email", {"old_email": task["old_email"], "new_email": resource["address"]})
            result = await client.replace_recovery_email(
                old_email=task["old_email"],
                new_email=resource["address"],
                code_provider=provider,
                verification_email=task.get("verification_email") or task.get("old_email") or None,
            )
            await _complete_step(task_id, "replace_recovery_email", {"old_email": task["old_email"], "new_email": resource["address"]})
    except Exception:
        rollback = await _rollback_rebind(task, resource)
        await update_task_status(task_id, "needs_manual", error_message="rebind_failed_with_rollback")
        publish_task_event(task_id, "needs_manual", rollback)
        raise

    old_resource = await db_manager.get_aux_email_resource_by_address(task.get("old_email", ""))
    if old_resource:
        await _mark_resource_available(int(old_resource["id"]))
    await _mark_resource_bound(int(resource["id"]), task["target_email"])
    await update_task_status(task_id, "success")
    publish_task_event(task_id, "success", {"resource": resource["address"]})
    return result


async def _maybe_rotate_resource(task_id: int, task: dict[str, Any]) -> dict[str, Any] | None:
    resource = await db_manager.get_aux_email_resource_by_id(int(task["resource_id"]))
    if not resource:
        return None
    notes = _notes_json(resource)
    replacement_address = notes.get("replacement_address")
    return await rotate_aux_email_resource(
        int(resource["id"]),
        replacement_address=replacement_address,
        max_fail_count=2,
        reason=f"task:{task_id}:code_delivery_failure",
    )


@celery_app.task(name="outlooker.protocol.ping")
def protocol_ping() -> dict[str, str]:
    """Minimal worker smoke task used before real protocol tasks are attached."""
    return {"status": "ok"}


@celery_app.task(name="outlooker.protocol.bind_secondary")
def protocol_bind_secondary(task_id: int) -> dict[str, Any]:
    async def _runner() -> dict[str, Any]:
        started_at = time.time()
        task = await db_manager.get_protocol_task(task_id)
        if task is None:
            raise RuntimeError("Protocol task not found")
        try:
            result = await _run_protocol_bind(task_id)
            record_protocol_task_metrics("bind_secondary", "success", time.time() - started_at)
            return result
        except TimeoutError as exc:
            rotation = await _maybe_rotate_resource(task_id, task)
            retry_count = int(task.get("retry_count") or 0) + 1
            await update_task_status(task_id, "failed", error_message=str(exc), retry_count=retry_count)
            await _fail_step(task_id, "bind_recovery_email", {"error": str(exc), "rotation": rotation})
            if rotation and rotation.get("replacement"):
                await db_manager.update_protocol_task(task_id, resource_id=int(rotation["replacement"]["id"]))
            record_protocol_task_metrics("bind_secondary", "failed", time.time() - started_at)
            raise
        except Exception as exc:  # noqa: BLE001
            retry_count = int(task.get("retry_count") or 0) + 1
            await update_task_status(task_id, "failed", error_message=str(exc), retry_count=retry_count)
            await _fail_step(task_id, "protocol_bind", {"error": str(exc)})
            record_protocol_task_metrics("bind_secondary", "failed", time.time() - started_at)
            raise

    return asyncio.run(_runner())


@celery_app.task(name="outlooker.protocol.rebind_secondary")
def protocol_rebind_secondary(task_id: int) -> dict[str, Any]:
    async def _runner() -> dict[str, Any]:
        started_at = time.time()
        task = await db_manager.get_protocol_task(task_id)
        if task is None:
            raise RuntimeError("Protocol task not found")
        try:
            result = await _run_protocol_rebind(task_id)
            record_protocol_task_metrics("rebind_secondary", "success", time.time() - started_at)
            return result
        except TimeoutError as exc:
            rotation = await _maybe_rotate_resource(task_id, task)
            retry_count = int(task.get("retry_count") or 0) + 1
            await update_task_status(task_id, "failed", error_message=str(exc), retry_count=retry_count)
            await _fail_step(task_id, "replace_recovery_email", {"error": str(exc), "rotation": rotation})
            if rotation and rotation.get("replacement"):
                await db_manager.update_protocol_task(task_id, resource_id=int(rotation["replacement"]["id"]))
            record_protocol_task_metrics("rebind_secondary", "failed", time.time() - started_at)
            raise
        except Exception as exc:  # noqa: BLE001
            current = await db_manager.get_protocol_task(task_id)
            if current and current.get("status") == "needs_manual":
                await _fail_step(task_id, "protocol_rebind", {"error": str(exc), "status": "needs_manual"})
                record_protocol_task_metrics("rebind_secondary", "needs_manual", time.time() - started_at)
                raise
            retry_count = int(task.get("retry_count") or 0) + 1
            await update_task_status(task_id, "failed", error_message=str(exc), retry_count=retry_count)
            await _fail_step(task_id, "protocol_rebind", {"error": str(exc)})
            record_protocol_task_metrics("rebind_secondary", "failed", time.time() - started_at)
            raise

    return asyncio.run(_runner())
