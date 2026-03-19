"""Channel-level statistics and health aggregation."""

from __future__ import annotations

from typing import Any

from ...db import db_manager


async def get_channel_stats(channel_id: int | None = None) -> dict[str, Any]:
    def _sync_stats(conn) -> dict[str, Any]:
        cursor = conn.cursor()
        where_channel = "WHERE channel_id = ?" if channel_id is not None else ""
        params = [channel_id] if channel_id is not None else []

        cursor.execute(
            f"SELECT COUNT(*) FROM channel_account_relations {where_channel}",
            params,
        )
        total_accounts = int(cursor.fetchone()[0])

        cursor.execute(
            f"SELECT COUNT(*) FROM channel_account_relations {where_channel} {'AND' if channel_id is not None else 'WHERE'} status = 'quarantine'",
            params,
        )
        quarantined_accounts = int(cursor.fetchone()[0])

        cursor.execute(
            f"SELECT COUNT(*) FROM allocation_leases {where_channel}",
            params,
        )
        total_leases = int(cursor.fetchone()[0])

        cursor.execute(
            f"SELECT COUNT(*) FROM allocation_leases {where_channel} {'AND' if channel_id is not None else 'WHERE'} status = 'active'",
            params,
        )
        active_leases = int(cursor.fetchone()[0])

        cursor.execute(
            f"SELECT COUNT(*) FROM aux_email_resources {where_channel}",
            params,
        )
        total_resources = int(cursor.fetchone()[0])

        cursor.execute(
            f"SELECT COUNT(*) FROM aux_email_resources {where_channel} {'AND' if channel_id is not None else 'WHERE'} status = 'quarantine'",
            params,
        )
        quarantined_resources = int(cursor.fetchone()[0])

        cursor.execute(
            f"SELECT COUNT(*) FROM aux_email_resources {where_channel} {'AND' if channel_id is not None else 'WHERE'} status = 'rotated'",
            params,
        )
        rotated_resources = int(cursor.fetchone()[0])

        task_params = [channel_id] if channel_id is not None else []
        task_where = "WHERE channel_id = ?" if channel_id is not None else ""
        cursor.execute(
            f"SELECT COUNT(*) FROM protocol_tasks {task_where}",
            task_params,
        )
        total_tasks = int(cursor.fetchone()[0])
        cursor.execute(
            f"SELECT COUNT(*) FROM protocol_tasks {task_where} {'AND' if channel_id is not None else 'WHERE'} status = 'success'",
            task_params,
        )
        success_tasks = int(cursor.fetchone()[0])
        cursor.execute(
            f"SELECT COUNT(*) FROM protocol_tasks {task_where} {'AND' if channel_id is not None else 'WHERE'} status = 'failed'",
            task_params,
        )
        failed_tasks = int(cursor.fetchone()[0])

        success_rate = (success_tasks / total_tasks) if total_tasks else 0.0
        failure_rate = (failed_tasks / total_tasks) if total_tasks else 0.0

        return {
            "channel_id": channel_id,
            "accounts": {
                "total": total_accounts,
                "quarantined": quarantined_accounts,
            },
            "leases": {
                "total": total_leases,
                "active": active_leases,
            },
            "resources": {
                "total": total_resources,
                "quarantined": quarantined_resources,
                "rotated": rotated_resources,
            },
            "tasks": {
                "total": total_tasks,
                "success": success_tasks,
                "failed": failed_tasks,
                "success_rate": success_rate,
                "failure_rate": failure_rate,
            },
        }

    return await db_manager._run_in_thread(_sync_stats)
