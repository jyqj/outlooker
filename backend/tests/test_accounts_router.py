#!/usr/bin/env python3
"""
账户路由器补充测试
测试账户管理、标签管理和批量操作
"""

from contextlib import closing

import pytest
from fastapi.testclient import TestClient

from app.mail_api import app, db_manager


client = TestClient(app)


@pytest.fixture(autouse=True)
def setup_and_teardown():
    """每个测试前后的设置和清理"""
    db_manager.init_database()
    with closing(db_manager.get_connection()) as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM accounts")
        cursor.execute("DELETE FROM account_tags")
        cursor.execute("DELETE FROM email_cache")
        cursor.execute("DELETE FROM email_cache_meta")
        conn.commit()
    yield


class TestAccountsPaged:
    """测试分页账户列表"""

    def test_get_accounts_paged_empty(self, admin_headers):
        """测试空账户列表分页"""
        response = client.get("/api/accounts/paged", headers=admin_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["items"] == []
        assert data["data"]["total"] == 0

    def test_get_accounts_paged_with_data(self, admin_headers):
        """测试有数据时的分页"""
        # 创建测试账户
        for i in range(15):
            client.post(
                "/api/accounts",
                json={
                    "email": f"test{i}@example.com",
                    "password": "",
                    "client_id": "",
                    "refresh_token": f"token{i}",
                },
                headers=admin_headers,
            )

        # 测试第一页
        response = client.get(
            "/api/accounts/paged?page=1&page_size=10",
            headers=admin_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert len(data["data"]["items"]) == 10
        assert data["data"]["total"] == 15

        # 测试第二页
        response = client.get(
            "/api/accounts/paged?page=2&page_size=10",
            headers=admin_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data["data"]["items"]) == 5

    def test_get_accounts_paged_with_search(self, admin_headers):
        """测试搜索功能"""
        # 创建测试账户
        client.post(
            "/api/accounts",
            json={
                "email": "alice@example.com",
                "password": "",
                "client_id": "",
                "refresh_token": "token1",
            },
            headers=admin_headers,
        )
        client.post(
            "/api/accounts",
            json={
                "email": "bob@example.com",
                "password": "",
                "client_id": "",
                "refresh_token": "token2",
            },
            headers=admin_headers,
        )

        # 搜索 alice
        response = client.get(
            "/api/accounts/paged?q=alice",
            headers=admin_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert len(data["data"]["items"]) == 1
        assert data["data"]["items"][0]["email"] == "alice@example.com"


class TestAccountTags:
    """测试账户标签管理"""

    def test_set_and_get_account_tags(self, admin_headers):
        """测试设置和获取账户标签"""
        email = "tagged@example.com"
        
        # 创建账户
        client.post(
            "/api/accounts",
            json={
                "email": email,
                "password": "",
                "client_id": "",
                "refresh_token": "token",
            },
            headers=admin_headers,
        )

        # 设置标签
        response = client.post(
            f"/api/account/{email}/tags",
            json={"email": email, "tags": ["vip", "test"]},
            headers=admin_headers,
        )
        assert response.status_code == 200
        assert response.json()["success"] is True

        # 获取标签
        response = client.get(
            f"/api/account/{email}/tags",
            headers=admin_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "vip" in data["data"]["tags"]
        assert "test" in data["data"]["tags"]

    def test_get_all_tags(self, admin_headers):
        """测试获取所有标签"""
        # 创建带标签的账户
        client.post(
            "/api/accounts",
            json={
                "email": "tag1@example.com",
                "password": "",
                "client_id": "",
                "refresh_token": "token1",
            },
            headers=admin_headers,
        )
        client.post(
            f"/api/account/tag1@example.com/tags",
            json={"email": "tag1@example.com", "tags": ["alpha", "beta"]},
            headers=admin_headers,
        )

        response = client.get("/api/accounts/tags", headers=admin_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "tags" in data["data"]
        assert "accounts" in data["data"]


class TestBatchOperations:
    """测试批量操作"""

    def test_batch_delete_accounts(self, admin_headers):
        """测试批量删除账户"""
        emails = []
        for i in range(3):
            email = f"delete{i}@example.com"
            emails.append(email)
            client.post(
                "/api/accounts",
                json={
                    "email": email,
                    "password": "",
                    "client_id": "",
                    "refresh_token": f"token{i}",
                },
                headers=admin_headers,
            )

        # 批量删除
        response = client.post(
            "/api/accounts/batch-delete",
            json={"emails": emails},
            headers=admin_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["deleted_count"] == 3

        # 验证已删除
        list_response = client.get("/api/accounts", headers=admin_headers)
        assert len(list_response.json()["data"]) == 0

    def test_batch_delete_empty_list(self, admin_headers):
        """测试批量删除空列表"""
        response = client.post(
            "/api/accounts/batch-delete",
            json={"emails": []},
            headers=admin_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is False

    def test_batch_update_tags_add(self, admin_headers):
        """测试批量添加标签"""
        emails = []
        for i in range(2):
            email = f"batchtag{i}@example.com"
            emails.append(email)
            client.post(
                "/api/accounts",
                json={
                    "email": email,
                    "password": "",
                    "client_id": "",
                    "refresh_token": f"token{i}",
                },
                headers=admin_headers,
            )

        # 批量添加标签
        response = client.post(
            "/api/accounts/batch-tags",
            json={"emails": emails, "tags": ["batch", "test"], "mode": "add"},
            headers=admin_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["updated_count"] == 2

        # 验证标签
        for email in emails:
            tag_response = client.get(
                f"/api/account/{email}/tags",
                headers=admin_headers,
            )
            tags = tag_response.json()["data"]["tags"]
            assert "batch" in tags
            assert "test" in tags

    def test_batch_update_tags_remove(self, admin_headers):
        """测试批量移除标签"""
        email = "remove-tag@example.com"
        client.post(
            "/api/accounts",
            json={
                "email": email,
                "password": "",
                "client_id": "",
                "refresh_token": "token",
            },
            headers=admin_headers,
        )
        client.post(
            f"/api/account/{email}/tags",
            json={"email": email, "tags": ["keep", "remove"]},
            headers=admin_headers,
        )

        # 批量移除标签
        response = client.post(
            "/api/accounts/batch-tags",
            json={"emails": [email], "tags": ["remove"], "mode": "remove"},
            headers=admin_headers,
        )
        assert response.status_code == 200

        # 验证标签已移除
        tag_response = client.get(
            f"/api/account/{email}/tags",
            headers=admin_headers,
        )
        tags = tag_response.json()["data"]["tags"]
        assert "keep" in tags
        assert "remove" not in tags

    def test_batch_update_tags_set(self, admin_headers):
        """测试批量替换标签"""
        email = "set-tag@example.com"
        client.post(
            "/api/accounts",
            json={
                "email": email,
                "password": "",
                "client_id": "",
                "refresh_token": "token",
            },
            headers=admin_headers,
        )
        client.post(
            f"/api/account/{email}/tags",
            json={"email": email, "tags": ["old1", "old2"]},
            headers=admin_headers,
        )

        # 批量替换标签
        response = client.post(
            "/api/accounts/batch-tags",
            json={"emails": [email], "tags": ["new1", "new2"], "mode": "set"},
            headers=admin_headers,
        )
        assert response.status_code == 200

        # 验证标签已替换
        tag_response = client.get(
            f"/api/account/{email}/tags",
            headers=admin_headers,
        )
        tags = tag_response.json()["data"]["tags"]
        assert "new1" in tags
        assert "new2" in tags
        assert "old1" not in tags
        assert "old2" not in tags


class TestAccountImportExport:
    """测试账户导入导出"""

    def test_import_accounts(self, admin_headers):
        """测试导入账户"""
        response = client.post(
            "/api/import",
            json={
                "accounts": [
                    {
                        "email": "import1@example.com",
                        "password": "pass1",
                        "client_id": "client1",
                        "refresh_token": "token1",
                    },
                    {
                        "email": "import2@example.com",
                        "password": "pass2",
                        "client_id": "client2",
                        "refresh_token": "token2",
                    },
                ],
                "merge_mode": "update",
            },
            headers=admin_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["added_count"] == 2

    def test_import_accounts_skip_mode(self, admin_headers):
        """测试导入账户 skip 模式"""
        # 先创建一个账户
        client.post(
            "/api/accounts",
            json={
                "email": "existing@example.com",
                "password": "",
                "client_id": "",
                "refresh_token": "original",
            },
            headers=admin_headers,
        )

        # 尝试导入同一账户
        response = client.post(
            "/api/import",
            json={
                "accounts": [
                    {
                        "email": "existing@example.com",
                        "password": "",
                        "client_id": "",
                        "refresh_token": "new",
                    },
                ],
                "merge_mode": "skip",
            },
            headers=admin_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["data"]["skipped_count"] == 1

    def test_export_accounts(self, admin_headers):
        """测试导出账户"""
        # 先创建账户
        client.post(
            "/api/accounts",
            json={
                "email": "export@example.com",
                "password": "secret",
                "client_id": "client",
                "refresh_token": "token",
            },
            headers=admin_headers,
        )

        response = client.get("/api/export", headers=admin_headers)
        assert response.status_code == 200
        assert "text/plain" in response.headers["content-type"]
        assert "export@example.com" in response.text


class TestAccountDetail:
    """测试账户详情"""

    def test_get_account_detail_not_found(self, admin_headers):
        """测试获取不存在的账户详情"""
        response = client.get(
            "/api/account/nonexistent@example.com",
            headers=admin_headers,
        )
        assert response.status_code == 404

    def test_get_account_detail_masked(self, admin_headers):
        """测试获取账户详情（敏感字段脱敏）"""
        email = "detail@example.com"
        client.post(
            "/api/accounts",
            json={
                "email": email,
                "password": "verysecret",
                "client_id": "myclient",
                "refresh_token": "mytoken123456",
            },
            headers=admin_headers,
        )

        response = client.get(f"/api/account/{email}", headers=admin_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["email"] == email
        assert data["data"]["has_password"] is True
        assert data["data"]["has_refresh_token"] is True
        # 验证脱敏
        assert "***" in data["data"]["password_preview"]
        assert "***" in data["data"]["refresh_token_preview"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
