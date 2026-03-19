"""Auxiliary email resource pool service."""

from __future__ import annotations

from typing import Any

from ...core.metrics import record_aux_resource_rotation
from ...db import db_manager


async def list_aux_email_resources(
    *,
    status: str | None = None,
    channel_id: int | None = None,
    limit: int = 100,
    offset: int = 0,
) -> dict[str, Any]:
    def _sync_list(conn) -> dict[str, Any]:
        cursor = conn.cursor()
        conditions: list[str] = []
        params: list[Any] = []
        if status:
            conditions.append("status = ?")
            params.append(status)
        if channel_id is not None:
            conditions.append("channel_id = ?")
            params.append(channel_id)
        where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""

        count_params = list(params)
        cursor.execute(
            f"SELECT COUNT(*) FROM aux_email_resources {where_clause}",
            count_params,
        )
        total_row = cursor.fetchone()
        total = int(total_row[0]) if total_row else 0

        params.extend([max(1, limit), max(0, offset)])
        cursor.execute(
            f"""
            SELECT
                id,
                address,
                provider,
                source_type,
                status,
                channel_id,
                fail_count,
                last_email_id,
                bound_account_email,
                notes,
                created_at,
                updated_at
            FROM aux_email_resources
            {where_clause}
            ORDER BY id DESC
            LIMIT ? OFFSET ?
            """,
            params,
        )
        return {"items": [dict(row) for row in cursor.fetchall()], "total": total}

    return await db_manager._run_in_thread(_sync_list)


async def create_aux_email_resource(**payload: Any) -> dict[str, Any]:
    resource_id = await db_manager.create_aux_email_resource(**payload)
    resource = await db_manager._run_in_thread(
        lambda conn: dict(
            conn.execute(
                """
                SELECT id, address, provider, source_type, status, channel_id,
                       fail_count, last_email_id, bound_account_email, notes, created_at, updated_at
                FROM aux_email_resources
                WHERE id = ?
                """,
                (resource_id,),
            ).fetchone()
        )
    )
    return resource


async def import_aux_email_resources(items: list[dict[str, Any]]) -> dict[str, Any]:
    created = 0
    failed = 0
    details: list[dict[str, Any]] = []
    for item in items:
        try:
            resource = await create_aux_email_resource(**item)
            created += 1
            details.append({"address": resource["address"], "status": "created"})
        except Exception as exc:  # noqa: BLE001
            failed += 1
            details.append({"address": item.get("address", ""), "status": "failed", "error": str(exc)})
    return {"requested": len(items), "created": created, "failed": failed, "details": details}


async def update_aux_email_resource(resource_id: int, **payload: Any) -> dict[str, Any]:
    updated = await db_manager.update_aux_email_resource(resource_id, **payload)
    if not updated:
        raise RuntimeError("Failed to update auxiliary email resource")
    resource = await db_manager._run_in_thread(
        lambda conn: dict(
            conn.execute(
                """
                SELECT id, address, provider, source_type, status, channel_id,
                       fail_count, last_email_id, bound_account_email, notes, created_at, updated_at
                FROM aux_email_resources
                WHERE id = ?
                """,
                (resource_id,),
            ).fetchone()
        )
    )
    return resource


async def bind_resources_to_channel(
    channel_id: int,
    resource_ids: list[int],
    *,
    status: str = "active",
) -> dict[str, Any]:
    updated = 0
    failed = 0
    for resource_id in resource_ids:
        resource = await db_manager.get_aux_email_resource_by_id(resource_id)
        if not resource:
            failed += 1
            continue
        ok = await db_manager.bind_resource_to_channel(channel_id, resource_id, status=status)
        if ok:
            await db_manager.update_aux_email_resource(resource_id, channel_id=channel_id)
            updated += 1
        else:
            failed += 1
    return {
        "channel_id": channel_id,
        "requested": len(resource_ids),
        "updated": updated,
        "failed": failed,
    }


async def list_channel_resources(channel_id: int) -> list[dict[str, Any]]:
    relations = await db_manager.list_channel_resource_relations(channel_id)
    resources: list[dict[str, Any]] = []
    for relation in relations:
        resource = await db_manager.get_aux_email_resource_by_id(int(relation["resource_id"]))
        if resource:
            resource["relation_status"] = relation["status"]
            resources.append(resource)
    return resources


async def get_allocatable_resource_for_channel(channel_id: int) -> dict[str, Any] | None:
    resources = await list_channel_resources(channel_id)
    for resource in resources:
        if resource.get("status") == "available" and resource.get("relation_status") == "active":
            return resource
    return None


async def record_resource_delivery_failure(
    resource_id: int,
    *,
    max_fail_count: int = 2,
    reason: str = "",
    replacement_address: str | None = None,
) -> dict[str, Any]:
    resource = await db_manager.get_aux_email_resource_by_id(resource_id)
    if resource is None:
        raise RuntimeError("Auxiliary email resource not found")

    fail_count = int(resource.get("fail_count") or 0) + 1
    next_status = resource["status"]
    replacement = None

    if fail_count >= max_fail_count:
        next_status = "quarantine" if not replacement_address else "rotated"

    notes = resource.get("notes", "") or ""
    if reason:
        notes = f"{notes}\nrotation_reason={reason}".strip()

    await db_manager.update_aux_email_resource(
        resource_id,
        fail_count=fail_count,
        status=next_status,
        notes=notes,
    )

    if fail_count >= max_fail_count and replacement_address:
        replacement = await create_aux_email_resource(
            address=replacement_address,
            provider=resource.get("provider", "custom"),
            source_type=resource.get("source_type", "manual"),
            status="available",
            channel_id=resource.get("channel_id"),
            notes=f"rotated from resource {resource_id}",
        )
        if resource.get("channel_id") is not None:
            await db_manager.bind_resource_to_channel(
                int(resource["channel_id"]),
                int(replacement["id"]),
                status="active",
            )

    updated_resource = await db_manager.get_aux_email_resource_by_id(resource_id)
    return {
        "resource": updated_resource,
        "replacement": replacement,
        "threshold_reached": fail_count >= max_fail_count,
    }


async def rotate_aux_email_resource(
    resource_id: int,
    *,
    replacement_address: str | None = None,
    max_fail_count: int = 2,
    reason: str = "",
) -> dict[str, Any]:
    result = await record_resource_delivery_failure(
        resource_id,
        max_fail_count=max_fail_count,
        reason=reason or "manual_rotation",
        replacement_address=replacement_address,
    )
    resource = result.get("resource") or {}
    record_aux_resource_rotation(str(resource.get("channel_id") or "unassigned"))
    return result
