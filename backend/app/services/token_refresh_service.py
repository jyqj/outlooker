"""Background token refresh service.

Periodically refreshes OAuth tokens for all accounts to prevent expiration.
Reads configuration from the system_config table (set via Settings page).
"""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from typing import Any

from ..auth.oauth import get_access_token
from ..db import db_manager
from .system_config_service import get_system_config_value
from .webhook_service import dispatch_event

logger = logging.getLogger(__name__)

_task: asyncio.Task[None] | None = None


async def _refresh_cycle() -> dict[str, Any]:
    """Run a single refresh cycle for all accounts."""
    from .email_service import load_accounts_config

    accounts = await load_accounts_config()
    if not accounts:
        return {"total": 0, "refreshed": 0, "failed": 0}

    sem = asyncio.Semaphore(5)
    refreshed = 0
    failed = 0

    async def refresh_one(email: str, info: dict[str, str]) -> None:
        nonlocal refreshed, failed
        async with sem:
            rt = info.get("refresh_token", "")
            if not rt:
                await db_manager.update_account_health(email, "token_invalid")
                failed += 1
                return
            try:
                access, new_rt = await get_access_token(rt, check_only=True)
                if access:
                    await db_manager.update_account_health(
                        email, "healthy",
                        refresh_token=new_rt if new_rt and new_rt != rt else None,
                    )
                    refreshed += 1
                else:
                    await db_manager.update_account_health(email, "token_expired")
                    failed += 1
            except Exception as exc:
                logger.warning("Token refresh failed for %s: %s", email, exc)
                await db_manager.update_account_health(email, "error")
                await dispatch_event("token_refresh_failed", {"email": email, "error": str(exc)})
                failed += 1

    tasks = [refresh_one(e, info) for e, info in accounts.items()]
    await asyncio.gather(*tasks, return_exceptions=True)

    summary = {"total": len(accounts), "refreshed": refreshed, "failed": failed}
    await db_manager.upsert_system_metric("token_refresh", {
        **summary,
        "last_run_at": datetime.now(timezone.utc).isoformat() + "Z",
    })
    logger.info("Token refresh cycle: %s", summary)
    return summary


async def _loop() -> None:
    """Main background loop that runs refresh cycles based on configured interval."""
    while True:
        try:
            enabled = await get_system_config_value("token_refresh_enabled", True)
            if not enabled:
                await asyncio.sleep(300)
                continue

            interval_hours = await get_system_config_value("token_refresh_interval_hours", 12)
            interval_hours = max(1, min(168, int(interval_hours)))

            await _refresh_cycle()
            await asyncio.sleep(interval_hours * 3600)
        except asyncio.CancelledError:
            break
        except Exception as exc:
            logger.error("Token refresh loop error: %s", exc, exc_info=True)
            await asyncio.sleep(600)


def start_background_refresh() -> None:
    """Start the background token refresh task (call from lifespan)."""
    global _task
    if _task is None or _task.done():
        _task = asyncio.create_task(_loop())
        logger.info("Token auto-refresh background task started")


def stop_background_refresh() -> None:
    """Cancel the background task (call on shutdown)."""
    global _task
    if _task and not _task.done():
        _task.cancel()
        _task = None
        logger.info("Token auto-refresh background task stopped")
