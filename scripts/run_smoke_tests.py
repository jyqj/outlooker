#!/usr/bin/env python3
"""
Quick smoke test script for Outlooker backend.

Usage:
    SMOKE_ADMIN_PASSWORD=your-password python scripts/run_smoke_tests.py

Environment variables:
    SMOKE_BASE_URL          默认 http://localhost:5001
    SMOKE_ADMIN_USERNAME    默认读取 ADMIN_USERNAME 或 'admin'
    SMOKE_ADMIN_PASSWORD    如果未提供则尝试 ADMIN_PASSWORD
    SMOKE_ADMIN_JWT         如果提供则跳过登录直接使用该 token
"""

from __future__ import annotations

import os
import sys
from typing import Dict

import requests

BASE_URL = os.getenv("SMOKE_BASE_URL", "http://localhost:5001").rstrip("/")
ADMIN_USERNAME = os.getenv("SMOKE_ADMIN_USERNAME") or os.getenv("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = os.getenv("SMOKE_ADMIN_PASSWORD") or os.getenv("ADMIN_PASSWORD")
PRESET_TOKEN = os.getenv("SMOKE_ADMIN_JWT")


def acquire_token() -> str:
    if PRESET_TOKEN:
        return PRESET_TOKEN
    if not ADMIN_PASSWORD:
        raise RuntimeError(
            "缺少管理员密码。请通过 SMOKE_ADMIN_PASSWORD 或 ADMIN_PASSWORD 提供。"
        )

    response = requests.post(
        f"{BASE_URL}/api/admin/login",
        json={"username": ADMIN_USERNAME, "password": ADMIN_PASSWORD},
        timeout=10,
    )
    response.raise_for_status()
    payload = response.json()
    token = payload.get("access_token")
    if not token:
        raise RuntimeError(f"登录未返回 token: {payload}")
    return token


def authorized_headers(token: str) -> Dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def check_accounts(token: str) -> None:
    response = requests.get(
        f"{BASE_URL}/api/accounts",
        headers=authorized_headers(token),
        timeout=10,
    )
    response.raise_for_status()
    data = response.json()
    if not data.get("success"):
        raise RuntimeError(f"/api/accounts 返回失败: {data}")


def check_system_metrics(token: str) -> None:
    response = requests.get(
        f"{BASE_URL}/api/system/metrics",
        headers=authorized_headers(token),
        timeout=10,
    )
    response.raise_for_status()


def main() -> int:
    try:
        token = acquire_token()
        check_accounts(token)
        check_system_metrics(token)
    except Exception as exc:  # noqa: BLE001 - 脚本需要捕获所有异常
        print(f"[SMOKE] ❌ 测试失败: {exc}", file=sys.stderr)
        return 1

    print("[SMOKE] ✅ 核心 API 正常响应")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

