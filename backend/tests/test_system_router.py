#!/usr/bin/env python3
"""
系统路由器测试
测试健康检查、系统配置和指标端点
"""

from contextlib import closing
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from app.mail_api import app, db_manager


client = TestClient(app)


@pytest.fixture(autouse=True)
def setup_and_teardown():
    """每个测试前后的设置和清理"""
    db_manager.init_database()
    yield


class TestHealthEndpoints:
    """测试健康检查端点"""

    def test_health_check(self):
        """测试基本健康检查"""
        response = client.get("/api/health")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "version" in data
        assert "timestamp" in data
        assert "components" in data
        assert data["components"]["database"] in ["healthy", "unhealthy"]

    def test_liveness_check(self):
        """测试存活检查"""
        response = client.get("/api/health/live")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "alive"
        assert "timestamp" in data

    def test_readiness_check(self):
        """测试就绪检查"""
        response = client.get("/api/health/ready")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ready"
        assert "timestamp" in data

    @patch("app.routers.system.db_manager.check_database_connection")
    def test_readiness_check_db_failure(self, mock_check):
        """测试数据库故障时的就绪检查"""
        mock_check.return_value = False
        response = client.get("/api/health/ready")
        assert response.status_code == 503
        data = response.json()
        assert "not ready" in data.get("message", "").lower() or "error_code" in data


class TestSystemConfig:
    """测试系统配置端点"""

    def test_get_system_config(self, admin_headers):
        """测试获取系统配置"""
        response = client.get("/api/system/config", headers=admin_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "email_limit" in data["data"]

    def test_update_system_config_valid(self, admin_headers):
        """测试更新有效的系统配置"""
        response = client.post(
            "/api/system/config",
            json={"email_limit": 10},
            headers=admin_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

        # 验证更新成功
        get_response = client.get("/api/system/config", headers=admin_headers)
        assert get_response.json()["data"]["email_limit"] == 10

    def test_update_system_config_invalid_low(self, admin_headers):
        """测试更新无效的系统配置（过低）"""
        response = client.post(
            "/api/system/config",
            json={"email_limit": 0},
            headers=admin_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is False
        assert "1-50" in data["message"]

    def test_update_system_config_invalid_high(self, admin_headers):
        """测试更新无效的系统配置（过高）"""
        response = client.post(
            "/api/system/config",
            json={"email_limit": 100},
            headers=admin_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is False
        assert "1-50" in data["message"]


class TestSystemMetrics:
    """测试系统指标端点"""

    def test_get_system_metrics(self, admin_headers):
        """测试获取系统指标"""
        response = client.get("/api/system/metrics", headers=admin_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "email_manager" in data["data"]
        assert "database" in data["data"]

    def test_get_system_metrics_structure(self, admin_headers):
        """测试系统指标结构完整性"""
        response = client.get("/api/system/metrics", headers=admin_headers)
        data = response.json()
        email_manager = data["data"]["email_manager"]

        # 验证邮件管理器指标
        expected_keys = [
            "cache_hits",
            "cache_misses",
            "accounts_count",
        ]
        for key in expected_keys:
            assert key in email_manager, f"Missing key: {key}"


class TestCacheRefresh:
    """测试缓存刷新端点"""

    def test_refresh_cache(self, admin_headers):
        """测试刷新缓存"""
        response = client.post("/api/system/cache/refresh", headers=admin_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "刷新" in data["message"]

    def test_refresh_cache_without_auth(self):
        """测试未认证刷新缓存"""
        response = client.post("/api/system/cache/refresh")
        assert response.status_code == 401


class TestSystemEndpointsAuth:
    """测试系统端点认证"""

    def test_config_requires_auth(self):
        """测试配置端点需要认证"""
        response = client.get("/api/system/config")
        assert response.status_code == 401

    def test_metrics_requires_auth(self):
        """测试指标端点需要认证"""
        response = client.get("/api/system/metrics")
        assert response.status_code == 401

    def test_cache_refresh_requires_auth(self):
        """测试缓存刷新需要认证"""
        response = client.post("/api/system/cache/refresh")
        assert response.status_code == 401


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
