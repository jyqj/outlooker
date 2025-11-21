#!/usr/bin/env python3
"""数据库管理器扩展测试"""

from contextlib import closing

import pytest
import pytest_asyncio
from app.database import db_manager, looks_like_guid


@pytest_asyncio.fixture(autouse=True)
async def reset_database():
    """每个测试前重置数据库"""
    db_manager.init_database()
    await db_manager.replace_all_accounts({})
    with closing(db_manager.get_connection()) as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM account_tags")
        cursor.execute("DELETE FROM email_cache")
        cursor.execute("DELETE FROM system_config")
        conn.commit()
    yield


class TestGUIDValidation:
    """测试GUID格式验证"""

    def test_looks_like_guid_valid(self):
        """测试有效的GUID格式"""
        valid_guids = [
            "12345678-1234-1234-1234-123456789abc",
            "ABCDEF01-2345-6789-ABCD-EF0123456789",
            "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
        ]
        for guid in valid_guids:
            assert looks_like_guid(guid) is True

    def test_looks_like_guid_invalid(self):
        """测试无效的GUID格式"""
        invalid_guids = [
            "not-a-guid",
            "12345678-1234-1234-1234",  # 太短
            "12345678-1234-1234-1234-123456789abcdef",  # 太长
            "12345678_1234_1234_1234_123456789abc",  # 错误分隔符
            "",
            None,
        ]
        for guid in invalid_guids:
            assert looks_like_guid(guid) is False


class TestAccountOperations:
    """测试账户CRUD操作"""

    @pytest.mark.asyncio
    async def test_add_account_success(self):
        """测试添加账户成功"""
        email = "test@example.com"
        password = "test_password"
        refresh_token = "test_refresh_token"
        client_id = "12345678-1234-1234-1234-123456789abc"

        success = await db_manager.add_account(
            email,
            password=password,
            refresh_token=refresh_token,
            client_id=client_id
        )
        assert success is True

        # 验证账户已添加
        account = await db_manager.get_account(email)
        assert account is not None
        assert account["password"] == password
        assert account["refresh_token"] == refresh_token
        assert account["client_id"] == client_id

    @pytest.mark.asyncio
    async def test_add_duplicate_account(self):
        """测试添加重复账户"""
        email = "test@example.com"
        
        # 第一次添加
        success1 = await db_manager.add_account(email, refresh_token="token1")
        assert success1 is True

        # 第二次添加相同邮箱
        success2 = await db_manager.add_account(email, refresh_token="token2")
        assert success2 is False

    @pytest.mark.asyncio
    async def test_update_account(self):
        """测试更新账户"""
        email = "test@example.com"
        
        # 添加账户
        await db_manager.add_account(email, password="old_pass", refresh_token="old_token")
        
        # 更新账户
        success = await db_manager.update_account(
            email,
            password="new_pass",
            refresh_token="new_token"
        )
        assert success is True

        # 验证更新
        account = await db_manager.get_account(email)
        assert account["password"] == "new_pass"
        assert account["refresh_token"] == "new_token"

    @pytest.mark.asyncio
    async def test_delete_account(self):
        """测试删除账户"""
        email = "test@example.com"
        
        # 添加账户
        await db_manager.add_account(email, refresh_token="token")
        
        # 删除账户
        success = await db_manager.delete_account(email)
        assert success is True

        # 验证已删除
        account = await db_manager.get_account(email)
        assert account is None

    @pytest.mark.asyncio
    async def test_account_exists(self):
        """测试检查账户是否存在"""
        email = "test@example.com"
        
        # 账户不存在
        exists = await db_manager.account_exists(email)
        assert exists is False

        # 添加账户
        await db_manager.add_account(email, refresh_token="token")
        
        # 账户存在
        exists = await db_manager.account_exists(email)
        assert exists is True

    @pytest.mark.asyncio
    async def test_get_all_accounts(self):
        """测试获取所有账户"""
        # 添加多个账户
        emails = ["test1@example.com", "test2@example.com", "test3@example.com"]
        for email in emails:
            await db_manager.add_account(email, refresh_token=f"token_{email}")

        # 获取所有账户
        accounts = await db_manager.get_all_accounts()
        assert len(accounts) == 3
        for email in emails:
            assert email in accounts

    @pytest.mark.asyncio
    async def test_replace_all_accounts(self):
        """测试替换所有账户"""
        # 添加初始账户
        await db_manager.add_account("old@example.com", refresh_token="old_token")

        # 替换为新账户
        new_accounts = {
            "new1@example.com": {
                "password": "pass1",
                "refresh_token": "token1",
                "client_id": "client1"
            },
            "new2@example.com": {
                "password": "pass2",
                "refresh_token": "token2",
                "client_id": "client2"
            }
        }
        success = await db_manager.replace_all_accounts(new_accounts)
        assert success is True

        # 验证旧账户已删除
        old_account = await db_manager.get_account("old@example.com")
        assert old_account is None

        # 验证新账户已添加
        all_accounts = await db_manager.get_all_accounts()
        assert len(all_accounts) == 2
        assert "new1@example.com" in all_accounts
        assert "new2@example.com" in all_accounts

    @pytest.mark.asyncio
    async def test_account_usage_default_and_mark_used(self):
        """测试账户使用状态默认值及标记为已使用"""
        email = "usage@example.com"

        # 添加账户，默认应为未使用
        await db_manager.add_account(email, refresh_token="usage_token")
        account = await db_manager.get_account(email)
        assert account is not None
        assert account["is_used"] is False
        assert account["last_used_at"] is None

        # 标记为已使用
        success = await db_manager.mark_account_used(email)
        assert success is True

        updated = await db_manager.get_account(email)
        assert updated is not None
        assert updated["is_used"] is True
        # last_used_at 应被填充为时间字符串
        assert updated["last_used_at"] is not None

    @pytest.mark.asyncio
    async def test_get_first_unused_account_email(self):
        """测试获取未使用账户邮箱"""
        # 没有账户时应返回 None
        first = await db_manager.get_first_unused_account_email()
        assert first is None

        # 添加两个账户
        await db_manager.add_account("a@example.com", refresh_token="t1")
        await db_manager.add_account("b@example.com", refresh_token="t2")

        # 标记其中一个为已使用
        await db_manager.mark_account_used("a@example.com")

        # 应返回未使用的那个
        unused = await db_manager.get_first_unused_account_email()
        assert unused == "b@example.com"
