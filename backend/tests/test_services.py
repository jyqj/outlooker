#!/usr/bin/env python3
"""services 模块的核心单元测试"""

import asyncio
import json
import sqlite3
from contextlib import closing

import pytest
import pytest_asyncio

from app.services import (
    email_manager,
    load_accounts_config,
    load_system_config,
    merge_accounts_data_to_db,
    set_system_config_value,
    SYSTEM_CONFIG_DEFAULTS,
    _normalize_email,
    _parse_account_line,
    _validate_account_info,
    extract_verification_code,
    extract_code_from_message,
)
from app.database import db_manager
from app.models import ImportAccountData


@pytest_asyncio.fixture(autouse=True)
async def reset_services_state():
    """确保每个测试前数据库与缓存处于干净状态"""
    db_manager.init_database()
    await db_manager.replace_all_accounts({})
    await email_manager.invalidate_accounts_cache()
    with closing(db_manager.get_connection()) as conn:
        cursor = conn.cursor()
        try:
            cursor.execute("DELETE FROM system_metrics")
        except sqlite3.OperationalError:
            pass
        cursor.execute("DELETE FROM system_config")
        conn.commit()


class TestAccountParsing:
    def test_parse_standard_format(self):
        email, info = _parse_account_line(
            "test@example.com----secret----refresh_token_abc----client_id_xyz"
        )
        assert email == "test@example.com"
        assert info["password"] == "secret"
        assert info["refresh_token"] == "refresh_token_abc"
        assert info["client_id"] == "client_id_xyz"

    def test_parse_simple_format(self):
        email, info = _parse_account_line("simple@example.com----token_only")
        assert email == "simple@example.com"
        assert info["password"] == ""
        assert info["refresh_token"] == "token_only"

    def test_parse_invalid_format(self):
        with pytest.raises(ValueError):
            _parse_account_line("invalid_format_line")

    def test_normalize_email(self):
        assert _normalize_email("  Test@Example.com  ") == "test@example.com"

    def test_validate_account_info_client_id(self):
        errors = _validate_account_info(
            "invalid@example.com",
            {"refresh_token": "token", "client_id": "not-a-guid"}
        )
        assert errors and "client_id" in errors[0]


class TestEmailManagerCache:
    @pytest.mark.asyncio
    async def test_cache_roundtrip_and_invalidation(self):
        email = "cached@example.com"
        await db_manager.add_account(email, password="first", refresh_token="token1")

        first = await email_manager.load_accounts(force_refresh=True)
        assert email in first
        assert first[email]["password"] == "first"

        # 更新数据库，但不刷新缓存，应该仍返回旧值
        await db_manager.update_account(email, password="second")
        second = await email_manager.load_accounts()
        assert second[email]["password"] == "first"

        # 使缓存失效后应看到新值
        await email_manager.invalidate_accounts_cache()
        third = await email_manager.load_accounts()
        assert third[email]["password"] == "second"


class TestEmailManagerMetrics:
    @pytest.mark.asyncio
    async def test_metrics_cache_counters(self):
        email = "metrics@example.com"
        await db_manager.add_account(email, refresh_token="token")
        await email_manager.invalidate_accounts_cache()

        await email_manager.load_accounts(force_refresh=True)
        await email_manager.load_accounts()

        metrics = await email_manager.get_metrics()
        assert metrics["cache_misses"] >= 1
        assert metrics["cache_hits"] >= 1
        assert metrics["db_loads"] >= 1
        assert "last_cache_refresh_at" in metrics


class TestEmailManagerConcurrency:
    @pytest.mark.asyncio
    async def test_concurrent_loads_share_single_db_call(self, monkeypatch):
        call_count = 0

        async def fake_get_all_accounts():
            nonlocal call_count
            call_count += 1
            await asyncio.sleep(0.01)
            return {
                "concurrent@example.com": {
                    "password": "",
                    "client_id": "test-client",
                    "refresh_token": "token",
                }
            }

        monkeypatch.setattr(db_manager, "get_all_accounts", fake_get_all_accounts)
        await email_manager.invalidate_accounts_cache()
        before_metrics = await email_manager.get_metrics()

        results = await asyncio.gather(
            email_manager.load_accounts(),
            email_manager.load_accounts(),
            email_manager.load_accounts(),
        )

        assert call_count == 1
        assert all("concurrent@example.com" in loaded for loaded in results)

        metrics = await email_manager.get_metrics()
        assert metrics["db_loads"] - before_metrics.get("db_loads", 0) == 1


class TestMergeAccounts:
    @pytest.mark.asyncio
    async def test_merge_add_and_update(self):
        accounts = [
            ImportAccountData(
                email="merge1@example.com",
                password="p1",
                client_id="",
                refresh_token="token_a",
            )
        ]

        result_add = await merge_accounts_data_to_db(accounts, merge_mode="update")
        assert result_add.added_count == 1
        assert result_add.updated_count == 0

        # 再次导入同一账户触发更新逻辑
        updated_accounts = [
            ImportAccountData(
                email="merge1@example.com",
                password="p2",
                client_id="",
                refresh_token="token_b",
            )
        ]
        result_update = await merge_accounts_data_to_db(updated_accounts, merge_mode="update")
        assert result_update.updated_count == 1

    @pytest.mark.asyncio
    async def test_merge_skip_mode_skips_existing_account(self):
        email = "skip@example.com"
        await db_manager.add_account(email, password="p1", refresh_token="token")

        accounts = [
            ImportAccountData(
                email=email,
                password="new",
                client_id="",
                refresh_token="token-new",
            )
        ]

        result = await merge_accounts_data_to_db(accounts, merge_mode="skip")
        assert result.skipped_count == 1
        assert result.updated_count == 0
        assert result.success
        assert result.details[0]["action"] == "skipped"

    @pytest.mark.asyncio
    async def test_merge_replace_requires_valid_accounts(self):
        result = await merge_accounts_data_to_db([], merge_mode="replace")
        assert result.success is False
        assert result.added_count == 0
        assert result.error_count == 0

    @pytest.mark.asyncio
    async def test_merge_skip_mode(self):
        base_accounts = [
            ImportAccountData(email="skip@example.com", refresh_token="token_base"),
        ]
        await merge_accounts_data_to_db(base_accounts, merge_mode="update")

        skip_accounts = [
            ImportAccountData(email="skip@example.com", refresh_token="token_new"),
        ]
        result_skip = await merge_accounts_data_to_db(skip_accounts, merge_mode="skip")
        assert result_skip.skipped_count == 1
        assert result_skip.updated_count == 0

        account = await db_manager.get_account("skip@example.com")
        assert account["refresh_token"] == "token_base"


@pytest.mark.asyncio
async def test_load_accounts_config_delegates_to_manager():
    await db_manager.add_account("delegate@example.com", refresh_token="token")
    accounts = await load_accounts_config(force_refresh=True)
    assert "delegate@example.com" in accounts


class TestSystemConfig:
    @pytest.mark.asyncio
    async def test_load_system_config_returns_defaults(self, tmp_path, monkeypatch):
        temp_config = tmp_path / "system_config.json"
        monkeypatch.setattr("app.services.SYSTEM_CONFIG_FILE", temp_config)
        config = await load_system_config()
        assert config["email_limit"] == SYSTEM_CONFIG_DEFAULTS["email_limit"]

    @pytest.mark.asyncio
    async def test_set_system_config_value_persists(self, monkeypatch, tmp_path):
        temp_config = tmp_path / "system_config.json"
        monkeypatch.setattr("app.services.SYSTEM_CONFIG_FILE", temp_config)

        await set_system_config_value("email_limit", 7)
        config = await load_system_config()
        assert config["email_limit"] == 7

        assert not temp_config.exists()

        db_value = await db_manager.get_system_config("email_limit")
        assert db_value == "7"


class TestSystemMetrics:
    @pytest.mark.asyncio
    async def test_upsert_and_fetch_metrics(self):
        await db_manager.upsert_system_metric("cache_hit_rate", {"value": 0.91})
        metrics = await db_manager.get_all_system_metrics()
        assert "cache_hit_rate" in metrics
        assert metrics["cache_hit_rate"]["value"].startswith("{")

    @pytest.mark.asyncio
    async def test_metrics_snapshot_persisted(self):
        await email_manager.get_metrics()
        metrics = await db_manager.get_all_system_metrics()
        assert "email_manager" in metrics

    @pytest.mark.asyncio
    async def test_email_cache_stats(self):
        email_data = {
            'subject': 'Hello',
            'sender': {'emailAddress': {'name': 'Tester', 'address': 'tester@example.com'}},
            'receivedDateTime': '2025-01-01T00:00:00Z',
            'bodyPreview': 'preview',
            'body': {'content': 'body', 'contentType': 'text'},
        }
        await db_manager.cache_email('stat@example.com', 'mid-1', email_data)
        stats = await db_manager.get_email_cache_stats()
        assert stats["total_messages"] >= 1


class TestOtpService:
    def test_extract_verification_code_from_plain_text(self):
        text = "Your verification code is 123456. Please do not share it with anyone."
        code = extract_verification_code(text)
        assert code == "123456"

    def test_extract_verification_code_with_keywords_and_html(self):
        html = """
        <html>
          <body>
            <p>尊敬的用户，您的验证码为 <b>987654</b> ，请在 5 分钟内完成验证。</p>
          </body>
        </html>
        """
        # 通过 extract_code_from_message 间接测试 HTML 清理与提取逻辑
        message = {
            "body": {"content": html, "contentType": "html"},
            "bodyPreview": "",
        }
        code = extract_code_from_message(message)
        assert code == "987654"

    def test_extract_verification_code_avoids_dates_and_amounts(self):
        text = "订单金额为 $1234.56，订单号 2024 将在 10 分钟内处理。"
        code = extract_verification_code(text)
        # 这里没有真正的验证码，应返回 None
        assert code is None
