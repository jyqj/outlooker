"""Account allocation service for channel-based picking."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

from ...core.metrics import update_channeling_metrics
from ...db import db_manager


async def list_channels() -> list[dict[str, Any]]:
    return await db_manager._run_in_thread(
        lambda conn: [
            dict(row)
            for row in conn.execute(
                """
                SELECT id, code, name, status, priority, pick_strategy, cooldown_seconds, proxy_url, proxy_group, notes, created_at, updated_at
                FROM channels
                ORDER BY priority DESC, id ASC
                """
            ).fetchall()
        ]
    )


async def create_channel(**payload: Any) -> dict[str, Any]:
    channel_id = await db_manager.create_channel(**payload)
    channel = await db_manager.get_channel(channel_id)
    if channel is None:
        raise RuntimeError("Failed to create channel")
    return channel


async def update_channel(channel_id: int, **payload: Any) -> dict[str, Any]:
    updated = await db_manager.update_channel(channel_id, **payload)
    if not updated:
        raise RuntimeError("Failed to update channel")
    channel = await db_manager.get_channel(channel_id)
    if channel is None:
        raise RuntimeError("Channel not found after update")
    return channel


async def resolve_channel_proxy(channel_id: int | None) -> str | None:
    if channel_id is None:
        return None
    channel = await db_manager.get_channel(channel_id)
    if not channel:
        return None
    proxy_url = (channel.get("proxy_url") or "").strip()
    return proxy_url or None


async def bind_accounts_to_channel(
    channel_id: int,
    emails: list[str],
    *,
    status: str = "active",
    weight: int = 100,
) -> dict[str, Any]:
    updated = 0
    failed = 0
    for email in emails:
        account = await db_manager.get_outlook_account(email)
        if not account:
            failed += 1
            continue
        ok = await db_manager.bind_account_to_channel(
            channel_id=channel_id,
            account_email=email,
            status=status,
            weight=weight,
        )
        if ok:
            updated += 1
        else:
            failed += 1
    return {
        "channel_id": channel_id,
        "requested": len(emails),
        "updated": updated,
        "failed": failed,
    }


async def allocate_account_for_channel(
    channel_id: int,
    *,
    leased_to: str = "",
    lease_ttl_seconds: int = 300,
) -> dict[str, Any]:
    """Allocate a single account for a channel and create a lease."""

    def _sync_allocate(conn) -> dict[str, Any]:
        conn.execute("BEGIN IMMEDIATE")
        try:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT car.account_email, c.cooldown_seconds
                FROM channel_account_relations car
                JOIN channels c
                  ON c.id = car.channel_id
                LEFT JOIN allocation_leases al
                  ON al.channel_id = car.channel_id
                 AND al.account_email = car.account_email
                 AND al.status = 'active'
                 AND datetime(al.expires_at) > datetime('now')
                WHERE car.channel_id = ?
                  AND car.status = 'active'
                  AND al.id IS NULL
                  AND (
                    car.last_assigned_at IS NULL
                    OR datetime(car.last_assigned_at, '+' || c.cooldown_seconds || ' seconds') <= datetime('now')
                  )
                ORDER BY car.weight DESC, car.last_assigned_at IS NOT NULL, car.last_assigned_at ASC, car.account_email ASC
                LIMIT 1
                """,
                (channel_id,),
            )
            row = cursor.fetchone()
            if not row:
                conn.commit()
                raise RuntimeError("No allocatable account found")

            account_email = row["account_email"]
            expires_at = (datetime.now(UTC) + timedelta(seconds=lease_ttl_seconds)).isoformat()
            cursor.execute(
                """
                INSERT INTO allocation_leases (
                    channel_id, account_email, leased_to, expires_at, status
                ) VALUES (?, ?, ?, ?, 'active')
                """,
                (channel_id, account_email, leased_to, expires_at),
            )
            lease_id = int(cursor.lastrowid)
            cursor.execute(
                """
                UPDATE channel_account_relations
                SET last_assigned_at = CURRENT_TIMESTAMP, updated_at = CURRENT_TIMESTAMP
                WHERE channel_id = ? AND account_email = ?
                """,
                (channel_id, account_email),
            )
            conn.commit()
            return {
                "channel_id": channel_id,
                "account_email": account_email,
                "lease_id": lease_id,
                "leased_to": leased_to,
                "expires_at": expires_at,
            }
        except Exception:
            conn.rollback()
            raise

    return await db_manager._run_in_thread(_sync_allocate)


async def report_channel_account_failure(
    channel_id: int,
    account_email: str,
    *,
    quarantine: bool = True,
) -> dict[str, Any]:
    relation = await db_manager.get_channel_account_relation(channel_id, account_email)
    if relation is None:
        raise RuntimeError("Channel-account relation not found")

    new_status = "quarantine" if quarantine else relation["status"]
    await db_manager.update_channel_account_relation(
        channel_id,
        account_email,
        status=new_status,
    )
    active_lease = await db_manager.get_active_allocation_lease(channel_id, account_email)
    if active_lease:
        await db_manager.release_allocation_lease(int(active_lease["id"]))
    update_channeling_metrics(
        str(channel_id),
        quarantined_accounts=1 if new_status == "quarantine" else 0,
        active_leases=0,
    )
    return {
        "channel_id": channel_id,
        "account_email": account_email,
        "status": new_status,
        "lease_released": bool(active_lease),
    }
