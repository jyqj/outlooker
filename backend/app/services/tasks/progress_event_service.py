"""Progress event helpers backed by Redis pub/sub."""

from __future__ import annotations

import asyncio
import json
from datetime import UTC, datetime
from typing import Any, AsyncIterator

import redis

from ...settings import get_settings

settings = get_settings()


def publish_task_event(task_id: int, step: str, detail: dict[str, Any] | None = None) -> bool:
    payload = {
        "task_id": task_id,
        "step": step,
        "detail": detail or {},
        "timestamp": datetime.now(UTC).isoformat(),
    }
    try:
        client = redis.from_url(settings.worker.redis_url, decode_responses=True)
        client.publish(settings.worker.redis_pubsub_channel, json.dumps(payload, ensure_ascii=False))
        client.close()
        return True
    except Exception:
        return False


async def iter_task_events() -> AsyncIterator[str]:
    client = redis.from_url(settings.worker.redis_url, decode_responses=True)
    pubsub = client.pubsub()
    try:
        try:
            pubsub.subscribe(settings.worker.redis_pubsub_channel)
        except Exception:
            yield "event: warning\ndata: {\"message\":\"redis_unavailable\"}\n\n"
            return
        while True:
            try:
                message = pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)
            except Exception:
                yield "event: warning\ndata: {\"message\":\"redis_stream_broken\"}\n\n"
                return
            if message and message.get("data"):
                payload = message["data"]
                yield f"data: {payload}\n\n"
            await asyncio.sleep(0.2)
    finally:
        pubsub.close()
        client.close()
