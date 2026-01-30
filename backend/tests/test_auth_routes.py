#!/usr/bin/env python3
"""后端认证与公共接口补充测试"""

import asyncio
from contextlib import closing
from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient

from app.mail_api import app, db_manager
from app.jwt_auth import get_password_hash
from app.routers import public_accounts
from app.rate_limiter import public_api_rate_limiter
from app.settings import get_settings


async def reset_admin_state() -> None:
    """清理管理员相关表，确保测试独立"""
    with closing(db_manager.get_connection()) as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM admin_refresh_tokens")
        cursor.execute("DELETE FROM admin_users")
        cursor.execute("DELETE FROM admin_login_attempts")
        cursor.execute("DELETE FROM admin_lockouts")
        conn.commit()


async def seed_admin_user(password: str = "Admin#123", username: str = "admin") -> None:
    """插入一个可登录的管理员账号"""
    await reset_admin_state()
    await db_manager.create_admin_user(username, get_password_hash(password))


@pytest.mark.asyncio
async def test_admin_login_sets_refresh_cookie():
    client = TestClient(app)
    await seed_admin_user()

    resp = client.post("/api/admin/login", json={"username": "admin", "password": "Admin#123"})
    assert resp.status_code == 200

    payload = resp.json()
    cookie_name = get_settings().admin_refresh_cookie_name

    assert payload["refresh_token"]
    assert resp.cookies.get(cookie_name) == payload["refresh_token"]


@pytest.mark.asyncio
async def test_refresh_token_rotation_revokes_old():
    client = TestClient(app)
    await seed_admin_user(password="Rotate#123")

    login = client.post("/api/admin/login", json={"username": "admin", "password": "Rotate#123"})
    assert login.status_code == 200
    refresh_token = login.json()["refresh_token"]

    refreshed = client.post("/api/admin/refresh", json={"refresh_token": refresh_token})
    assert refreshed.status_code == 200
    new_refresh_token = refreshed.json()["refresh_token"]
    assert new_refresh_token != refresh_token

    # 旧 token 已被撤销，应无法再次刷新
    retry = client.post("/api/admin/refresh", json={"refresh_token": refresh_token})
    assert retry.status_code == 401


@pytest.mark.asyncio
async def test_logout_revokes_refresh_cookie():
    client = TestClient(app)
    await seed_admin_user(password="Logout#123")

    login = client.post("/api/admin/login", json={"username": "admin", "password": "Logout#123"})
    refresh_token = login.json()["refresh_token"]

    logout = client.post("/api/admin/logout", json={"refresh_token": refresh_token})
    assert logout.status_code == 200

    # 返回头应包含删除刷新 Cookie 的指示
    cookie_header = logout.headers.get("set-cookie", "")
    assert get_settings().admin_refresh_cookie_name in cookie_header

    # 被注销的 refresh token 不能再用于刷新
    retry = client.post("/api/admin/refresh", json={"refresh_token": refresh_token})
    assert retry.status_code == 401


@pytest.mark.asyncio
async def test_public_api_requires_token():
    client = TestClient(app)

    resp = client.get("/api/public/account-unused")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_public_api_rate_limit(monkeypatch):
    client = TestClient(app)
    token = get_settings().public_api_token

    monkeypatch.setattr(
        public_api_rate_limiter,
        "is_allowed",
        AsyncMock(return_value=(False, 5)),
    )

    resp = client.get("/api/public/account-unused", headers={"X-Public-Token": token})
    assert resp.status_code == 429
    assert "5" in resp.json().get("detail", "")


@pytest.mark.asyncio
async def test_temp_messages_handles_imap_error(monkeypatch):
    client = TestClient(app)
    token = get_settings().public_api_token
    mock_client = AsyncMock()
    mock_client.get_messages_with_content = AsyncMock(side_effect=Exception("imap boom"))
    mock_client.cleanup = AsyncMock()

    monkeypatch.setattr("app.routers.emails.IMAPEmailClient", lambda *args, **kwargs: mock_client)

    payload = {
        "email": "temp@example.com",
        "password": "",
        "client_id": "",
        "refresh_token": "temp-token",
        "page": 1,
        "page_size": 1,
        "top": 1,
    }

    resp = client.post("/api/temp-messages", json=payload, headers={"X-Public-Token": token})
    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is False
    assert "失败" in body["message"]
