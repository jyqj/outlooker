"""Webhook dispatch service.

Reads webhook configuration from system_config and dispatches events
asynchronously. Supports HMAC-SHA256 signing and automatic retries.
"""
from __future__ import annotations

import asyncio
import hashlib
import hmac
import json
import logging
import time
from typing import Any

import httpx

from .system_config_service import get_system_config_value

logger = logging.getLogger(__name__)

MAX_RETRIES = 3
RETRY_DELAYS = [1, 3, 10]

_background_tasks: set[asyncio.Task[None]] = set()


async def _get_webhook_config() -> dict[str, Any] | None:
    enabled = await get_system_config_value("webhook_enabled", False)
    if not enabled:
        return None
    url = await get_system_config_value("webhook_url", "")
    if not url:
        return None
    secret = await get_system_config_value("webhook_secret", "")
    events_str = await get_system_config_value(
        "webhook_events", "verification_code_received,token_refresh_failed"
    )
    events = [e.strip() for e in str(events_str).split(",") if e.strip()]
    return {"url": url, "secret": secret, "events": events}


def _sign_payload(payload: bytes, secret: str) -> str:
    return hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()


async def _send_with_retry(url: str, headers: dict[str, str], body: bytes) -> bool:
    for attempt in range(MAX_RETRIES):
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.post(url, content=body, headers=headers)
                if 200 <= resp.status_code < 300:
                    return True
                logger.warning("Webhook %s returned %s", url, resp.status_code)
        except Exception as exc:
            logger.warning("Webhook attempt %d failed: %s", attempt + 1, exc)
        if attempt < MAX_RETRIES - 1:
            await asyncio.sleep(RETRY_DELAYS[attempt])
    return False


async def dispatch_event(event_type: str, payload: dict[str, Any]) -> None:
    """Dispatch a webhook event. Non-blocking — fires as a background task."""
    config = await _get_webhook_config()
    if not config:
        return
    if event_type not in config["events"]:
        return

    body_dict = {
        "event": event_type,
        "timestamp": int(time.time()),
        "data": payload,
    }
    body = json.dumps(body_dict, ensure_ascii=False).encode()

    headers: dict[str, str] = {"Content-Type": "application/json"}
    if config["secret"]:
        headers["X-Signature"] = _sign_payload(body, config["secret"])

    task = asyncio.create_task(_send_with_retry(config["url"], headers, body))
    _background_tasks.add(task)
    task.add_done_callback(_background_tasks.discard)
