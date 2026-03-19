from __future__ import annotations

import asyncio
from contextlib import closing
from unittest.mock import MagicMock

from fastapi.testclient import TestClient

from app.mail_api import app, db_manager
from app.routers import outlook_protocol


client = TestClient(app)


def _reset_protocol_state() -> None:
    db_manager.init_database()
    with closing(db_manager.get_connection()) as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM protocol_task_steps")
        cursor.execute("DELETE FROM protocol_tasks")
        cursor.execute("DELETE FROM channel_resource_relations")
        cursor.execute("DELETE FROM aux_email_resources")
        cursor.execute("DELETE FROM accounts")
        conn.commit()


def test_bind_queue_creates_protocol_task(monkeypatch, admin_headers):
    _reset_protocol_state()
    monkeypatch.setattr(outlook_protocol, "_ensure_protocol_enabled", lambda: None)
    delay = MagicMock()
    monkeypatch.setattr(outlook_protocol.protocol_bind_secondary, "delay", delay)

    response = client.post(
        "/api/outlook/protocol/bind",
        json={
            "email": "bind-target@example.com",
            "password": "secret-pass",
            "recovery_email": "bind-resource@example.com",
            "static_code": "123456",
            "queue": True,
        },
        headers=admin_headers,
    )

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    task_id = int(body["data"]["task_id"])

    task = asyncio.run(db_manager.get_protocol_task(task_id))
    resource = asyncio.run(db_manager.get_aux_email_resource_by_address("bind-resource@example.com"))

    assert task is not None
    assert task["task_type"] == "bind_secondary"
    assert task["target_email"] == "bind-target@example.com"
    assert resource is not None
    assert resource["address"] == "bind-resource@example.com"
    delay.assert_called_once_with(task_id)


def test_replace_queue_creates_protocol_task(monkeypatch, admin_headers):
    _reset_protocol_state()
    monkeypatch.setattr(outlook_protocol, "_ensure_protocol_enabled", lambda: None)
    delay = MagicMock()
    monkeypatch.setattr(outlook_protocol.protocol_rebind_secondary, "delay", delay)

    response = client.post(
        "/api/outlook/protocol/replace",
        json={
            "email": "replace-target@example.com",
            "password": "secret-pass",
            "old_email": "old-recovery@example.com",
            "new_email": "new-recovery@example.com",
            "static_code": "654321",
            "queue": True,
        },
        headers=admin_headers,
    )

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    task_id = int(body["data"]["task_id"])

    task = asyncio.run(db_manager.get_protocol_task(task_id))
    resource = asyncio.run(db_manager.get_aux_email_resource_by_address("new-recovery@example.com"))

    assert task is not None
    assert task["task_type"] == "rebind_secondary"
    assert task["old_email"] == "old-recovery@example.com"
    assert task["new_email"] == "new-recovery@example.com"
    assert resource is not None
    delay.assert_called_once_with(task_id)
