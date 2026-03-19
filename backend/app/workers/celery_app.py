"""Celery application bootstrap for Outlook background tasks."""

from __future__ import annotations

from celery import Celery

from ..settings import get_settings

settings = get_settings()

celery_app = Celery(
    "outlooker",
    broker=settings.worker.celery_broker_url,
    backend=settings.worker.celery_result_backend,
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Asia/Shanghai",
    enable_utc=True,
    task_track_started=True,
    result_expires=3600,
)

celery_app.autodiscover_tasks(
    [
        "app.workers.protocol_tasks",
    ],
    force=True,
)
