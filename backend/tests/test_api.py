#!/usr/bin/env python3
"""
API测试用例
基础的smoke test，确保关键接口正常工作
"""

from contextlib import closing

import pytest
from unittest.mock import patch, AsyncMock
from fastapi.testclient import TestClient
from app.mail_api import app, db_manager
from app.jwt_auth import create_access_token

# 创建测试客户端
client = TestClient(app)

@pytest.fixture(autouse=True)
def setup_and_teardown():
    """每个测试前后的设置和清理"""
    # 测试前：确保数据库已初始化
    db_manager.init_database()
    with closing(db_manager.get_connection()) as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM accounts")
        cursor.execute("DELETE FROM account_tags")
        cursor.execute("DELETE FROM email_cache")
        conn.commit()
    yield
    # 测试后：可以在这里清理测试数据（如果需要）
    pass

class TestPublicEndpoints:
    """测试公开端点"""
    
    def test_root_endpoint(self):
        """测试根路径返回HTML页面"""
        response = client.get("/")
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]
    
    def test_admin_page(self):
        """测试管理页面可访问"""
        response = client.get("/admin")
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]
    
    def test_messages_without_email(self):
        """测试未提供邮箱时的错误处理"""
        response = client.get("/api/messages")
        assert response.status_code == 422  # Validation error

class TestAdminEndpoints:
    """测试需要管理员权限的端点"""
    
    def test_admin_verify_route_disabled_by_default(self):
        """默认情况下 Legacy token 接口不可用"""
        response = client.post("/api/admin/verify", json={"token": "legacy-placeholder"})
        assert response.status_code == 404
    
    def test_get_accounts_without_auth(self):
        """测试未认证访问账户列表"""
        response = client.get("/api/accounts")
        assert response.status_code == 401
    
    def test_get_accounts_with_auth(self, admin_headers):
        """测试已认证访问账户列表"""
        response = client.get("/api/accounts", headers=admin_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "data" in data
    
    def test_get_system_config_without_auth(self):
        """测试未认证访问系统配置"""
        response = client.get("/api/system/config")
        assert response.status_code == 401
    
    def test_get_system_config_with_auth(self, admin_headers):
        """测试已认证访问系统配置"""
        response = client.get("/api/system/config", headers=admin_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "data" in data
        assert "email_limit" in data["data"]

    def test_get_system_metrics_without_auth(self):
        """测试未认证访问系统指标"""
        response = client.get("/api/system/metrics")
        assert response.status_code == 401

    def test_get_system_metrics_with_auth(self, admin_headers):
        """测试已认证访问系统指标"""
        response = client.get("/api/system/metrics", headers=admin_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "email_manager" in data["data"]
    
    def test_refresh_cache_with_auth(self, admin_headers):
        """测试刷新缓存接口"""
        response = client.post("/api/system/cache/refresh", headers=admin_headers)
        assert response.status_code == 200
        payload = response.json()
        assert payload["success"] is True

    def test_update_system_config_with_auth(self, admin_headers):
        """测试更新系统配置"""
        response = client.post(
            "/api/system/config",
            json={"email_limit": 3},
            headers=admin_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
    
    def test_export_without_auth(self):
        """测试未认证导出账户"""
        response = client.get("/api/export")
        assert response.status_code == 401
    
    def test_import_without_auth(self):
        """测试未认证导入账户"""
        response = client.post("/api/import", json={"accounts": [], "merge_mode": "update"})
        assert response.status_code == 401

class TestAccountImport:
    """测试账户导入功能"""
    
    def test_parse_import_text_standard_format(self, admin_headers):
        """测试解析标准格式的导入文本"""
        import_text = "test@example.com----password----refresh_token_abc----client_id_123"
        response = client.post(
            "/api/parse-import-text",
            json={"text": import_text},
            headers=admin_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert len(data["data"]["accounts"]) == 1
        account = data["data"]["accounts"][0]
        assert account["email"] == "test@example.com"
        assert account["password"] == "password"
        assert account["refresh_token"] == "refresh_token_abc"
        assert account["client_id"] == "client_id_123"
    
    def test_parse_import_text_simple_format(self, admin_headers):
        """测试解析简化格式的导入文本"""
        import_text = "test@example.com----refresh_token_abc"
        response = client.post(
            "/api/parse-import-text",
            json={"text": import_text},
            headers=admin_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert len(data["data"]["accounts"]) == 1
        account = data["data"]["accounts"][0]
        assert account["email"] == "test@example.com"
        assert account["refresh_token"] == "refresh_token_abc"
    
    def test_parse_import_text_ignore_comments(self, admin_headers):
        """测试忽略注释行"""
        import_text = """# This is a comment
test@example.com----refresh_token_abc
# Another comment
"""
        response = client.post(
            "/api/parse-import-text",
            json={"text": import_text},
            headers=admin_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert len(data["data"]["accounts"]) == 1


class TestAccountCrud:
    """测试账户增删改查接口"""

    def test_account_lifecycle(self, jwt_headers):
        payload = {
            "email": "crud@example.com",
            "password": "secret",
            "client_id": "",
            "refresh_token": "token123",
        }

        # create
        response = client.post("/api/accounts", json=payload, headers=jwt_headers)
        assert response.status_code == 200
        body = response.json()
        if not body["success"]:
            raise AssertionError(f"response={body}")

        # detail
        detail = client.get("/api/account/crud@example.com", headers=jwt_headers)
        assert detail.status_code == 200
        detail_data = detail.json()["data"]
        assert detail_data["has_refresh_token"] is True

        # update
        payload["password"] = "updated"
        payload["refresh_token"] = "token456"
        response = client.put("/api/account/crud@example.com", json=payload, headers=jwt_headers)
        assert response.status_code == 200
        update_body = response.json()
        if not update_body["success"]:
            raise AssertionError(f"update_response={update_body}")

        # delete
        response = client.delete("/api/account/crud@example.com", headers=jwt_headers)
        assert response.status_code == 200
        delete_body = response.json()
        if not delete_body["success"]:
            raise AssertionError(f"delete_response={delete_body}")


class TestPublicAccountEndpoints:
    """测试公共邮箱账户接口"""

    def test_get_unused_account_when_empty(self):
        """当没有账户时，应返回暂无未使用邮箱"""
        response = client.get("/api/public/account-unused")
        assert response.status_code == 200
        body = response.json()
        assert body["success"] is False
        assert "暂无未使用的邮箱" in body["message"]

    def test_get_unused_account_success(self, jwt_headers):
        """存在账户时，应返回一个未使用的邮箱"""
        # 先通过受保护接口创建账户
        payload = {
            "email": "unused@example.com",
            "password": "",
            "client_id": "",
            "refresh_token": "token-unused",
        }
        create_resp = client.post("/api/accounts", json=payload, headers=jwt_headers)
        assert create_resp.status_code == 200
        assert create_resp.json()["success"] is True

        response = client.get("/api/public/account-unused")
        assert response.status_code == 200
        body = response.json()
        assert body["success"] is True
        assert body["data"]["email"] == "unused@example.com"

    def test_mark_account_used_and_delete_via_public_api(self, jwt_headers):
        """通过公共接口标记已用并删除账户"""
        email = "public@example.com"
        payload = {
            "email": email,
            "password": "",
            "client_id": "",
            "refresh_token": "token-public",
        }
        # 使用受保护接口创建账户
        create_resp = client.post("/api/accounts", json=payload, headers=jwt_headers)
        assert create_resp.status_code == 200
        assert create_resp.json()["success"] is True

        # 公共接口标记为已使用
        mark_resp = client.post(f"/api/public/account/{email}/used")
        assert mark_resp.status_code == 200
        mark_body = mark_resp.json()
        assert mark_body["success"] is True

        # 公共接口删除账户
        delete_resp = client.delete(f"/api/public/account/{email}")
        assert delete_resp.status_code == 200
        delete_body = delete_resp.json()
        assert delete_body["success"] is True

class TestDatabase:
    """测试数据库操作"""
    
    @pytest.mark.asyncio
    async def test_add_and_get_account(self):
        """测试添加和获取账户"""
        email = "test_db@example.com"
        password = "test_password"
        refresh_token = "test_refresh_token"
        
        # 添加账户（会自动加密）
        success = await db_manager.add_account(email, password=password, refresh_token=refresh_token)
        assert success is True
        
        # 获取账户（会自动解密）
        account = await db_manager.get_account(email)
        assert account is not None
        # get_account 返回的是解密后的值
        assert account["password"] == password
        assert account["refresh_token"] == refresh_token
        
        # 清理
        await db_manager.delete_account(email)
    
    @pytest.mark.asyncio
    async def test_account_exists(self):
        """测试检查账户是否存在"""
        email = "test_exists@example.com"
        
        # 账户不存在
        exists = await db_manager.account_exists(email)
        assert exists is False
        
        # 添加账户
        await db_manager.add_account(email, refresh_token="test_token")
        
        # 账户存在
        exists = await db_manager.account_exists(email)
        assert exists is True
        
        # 清理
        await db_manager.delete_account(email)
    
    @pytest.mark.asyncio
    async def test_update_account(self):
        """测试更新账户"""
        email = "test_update@example.com"
        
        # 添加账户（会自动加密）
        await db_manager.add_account(email, password="old_password", refresh_token="old_token")
        
        # 更新账户（会自动加密）
        success = await db_manager.update_account(email, password="new_password", refresh_token="new_token")
        assert success is True
        
        # 验证更新（get_account 会自动解密）
        account = await db_manager.get_account(email)
        assert account["password"] == "new_password"
        assert account["refresh_token"] == "new_token"
        
        # 清理
        await db_manager.delete_account(email)


class TestEmailEndpoints:
    """测试邮件相关接口"""

    @patch('app.services.email_manager.get_messages')
    @pytest.mark.asyncio
    async def test_get_messages_success(self, mock_get_messages, jwt_headers):
        """测试成功获取邮件列表"""
        # 准备测试数据：添加一个账户
        test_email = "test@example.com"
        await db_manager.add_account(test_email, refresh_token="test_token")
        
        # Mock EmailManager 返回
        mock_messages = [
            {
                "id": "msg1",
                "subject": "Test Email",
                "from": {"emailAddress": {"address": "sender@example.com", "name": "Sender"}},
                "receivedDateTime": "2024-01-01T00:00:00",
                "bodyPreview": "Test preview",
                "body": {"content": "Test content", "contentType": "text"}
            }
        ]
        mock_get_messages.return_value = mock_messages
        
        # 发起请求
        response = client.get(f"/api/messages?email={test_email}&page=1&page_size=5")
        
        # 验证响应
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "items" in data["data"]
        assert len(data["data"]["items"]) == 1
        assert data["data"]["page"] == 1
        assert data["data"]["page_size"] == 5
        
        # 清理
        await db_manager.delete_account(test_email)

    def test_get_messages_email_not_configured(self):
        """测试邮箱未配置返回错误"""
        response = client.get("/api/messages?email=nonexistent@example.com")
        assert response.status_code == 404
        data = response.json()
        assert "detail" in data
        assert "未在配置中找到" in data["detail"]

    @patch('app.routers.emails.IMAPEmailClient')
    def test_temp_messages_success(self, mock_imap_client):
        """测试临时账户获取邮件"""
        # Mock IMAP 客户端
        mock_instance = AsyncMock()
        mock_instance.get_messages_with_content = AsyncMock(return_value=[
            {
                "id": "msg1",
                "subject": "Temp Email",
                "from": {"emailAddress": {"address": "temp@example.com", "name": "Temp"}},
                "receivedDateTime": "2024-01-01T00:00:00",
                "bodyPreview": "Temp preview",
                "body": {"content": "Temp content", "contentType": "text"}
            }
        ])
        mock_instance.cleanup = AsyncMock()
        mock_imap_client.return_value = mock_instance
        
        # 发起请求
        response = client.post("/api/temp-messages", json={
            "email": "temp@example.com",
            "refresh_token": "temp_token",
            "page": 1,
            "page_size": 5
        })
        
        # 验证响应
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "items" in data["data"]

    @patch('app.services.email_manager.get_messages')
    @pytest.mark.asyncio
    async def test_test_email_success(self, mock_get_messages):
        """测试邮件连接测试接口"""
        # 准备测试数据
        test_email = "test@example.com"
        await db_manager.add_account(test_email, refresh_token="test_token")
        
        # Mock 返回
        mock_get_messages.return_value = [
            {
                "id": "msg1",
                "subject": "Test",
                "from": {"emailAddress": {"address": "sender@example.com"}},
                "receivedDateTime": "2024-01-01T00:00:00",
                "bodyPreview": "Preview",
                "body": {"content": "Content", "contentType": "text"}
            }
        ]
        
        # 发起请求
        response = client.post("/api/test-email", json={"email": test_email})
        
        # 验证响应
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"] is not None
        
        # 清理
        await db_manager.delete_account(test_email)

    @patch('app.routers.emails.IMAPEmailClient')
    def test_test_email_no_messages(self, mock_imap_client):
        """测试邮箱无邮件的情况"""
        mock_instance = AsyncMock()
        mock_instance.get_messages_with_content = AsyncMock(return_value=[])
        mock_instance.cleanup = AsyncMock()
        mock_imap_client.return_value = mock_instance

        response = client.post("/api/test-email", json={
            "email": "empty@example.com",
            "refresh_token": "valid_token"
        })
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"] is None
        assert "暂无邮件" in data["message"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
