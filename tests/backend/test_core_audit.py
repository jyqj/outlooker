"""Tests for audit logging."""

import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from datetime import datetime, timezone

from app.core.audit import (
    AuditLogger,
    AuditEvent,
    AuditEventType,
    audit_logger,
    init_audit_logger,
)


class TestAuditEventType:
    """审计事件类型测试"""

    def test_login_events_exist(self):
        """测试登录相关事件类型存在"""
        assert AuditEventType.LOGIN_SUCCESS.value == "login_success"
        assert AuditEventType.LOGIN_FAILED.value == "login_failed"
        assert AuditEventType.LOGOUT.value == "logout"

    def test_account_events_exist(self):
        """测试账户相关事件类型存在"""
        assert AuditEventType.ACCOUNT_CREATED.value == "account_created"
        assert AuditEventType.ACCOUNT_UPDATED.value == "account_updated"
        assert AuditEventType.ACCOUNT_DELETED.value == "account_deleted"

    def test_rate_limit_event_exists(self):
        """测试速率限制事件类型存在"""
        assert AuditEventType.RATE_LIMIT_EXCEEDED.value == "rate_limit_exceeded"


class TestAuditEvent:
    """审计事件模型测试"""

    def test_event_creation(self):
        """测试事件创建"""
        event = AuditEvent(
            event_type=AuditEventType.LOGIN_SUCCESS,
            timestamp=datetime.now(timezone.utc),
            user_id="admin",
            ip_address="192.168.1.1",
        )
        assert event.event_type == AuditEventType.LOGIN_SUCCESS
        assert event.user_id == "admin"
        assert event.ip_address == "192.168.1.1"
        assert event.success is True  # 默认值

    def test_event_with_failure(self):
        """测试失败事件"""
        event = AuditEvent(
            event_type=AuditEventType.LOGIN_FAILED,
            timestamp=datetime.now(timezone.utc),
            success=False,
            error_message="密码错误",
        )
        assert event.success is False
        assert event.error_message == "密码错误"

    def test_event_model_dump(self):
        """测试事件序列化"""
        event = AuditEvent(
            event_type=AuditEventType.LOGIN_SUCCESS,
            timestamp=datetime.now(timezone.utc),
        )
        data = event.model_dump()
        assert "event_type" in data
        assert "timestamp" in data
        assert "success" in data


class TestAuditLogger:
    """审计日志器测试"""

    @pytest.fixture
    def auditor(self):
        """创建审计日志器实例"""
        return AuditLogger()

    @pytest.fixture
    def auditor_with_db(self):
        """创建带数据库管理器的审计日志器"""
        mock_db = MagicMock()
        mock_db.store_audit_event = AsyncMock()
        return AuditLogger(db_manager=mock_db)

    @pytest.mark.asyncio
    async def test_log_basic(self, auditor):
        """测试基本日志记录"""
        # 不应该抛出异常
        await auditor.log(
            AuditEventType.LOGIN_SUCCESS,
            ip_address="192.168.1.1",
            user_id="admin",
        )

    @pytest.mark.asyncio
    async def test_log_with_db(self, auditor_with_db):
        """测试带数据库的日志记录"""
        await auditor_with_db.log(
            AuditEventType.LOGIN_SUCCESS,
            ip_address="192.168.1.1",
            user_id="admin",
        )
        
        # 应该调用数据库存储
        auditor_with_db._db_manager.store_audit_event.assert_called_once()

    @pytest.mark.asyncio
    async def test_log_login_success(self, auditor):
        """测试记录成功的登录"""
        await auditor.log_login(
            ip_address="192.168.1.1",
            username="admin",
            success=True,
        )

    @pytest.mark.asyncio
    async def test_log_login_failure(self, auditor):
        """测试记录失败的登录"""
        await auditor.log_login(
            ip_address="192.168.1.1",
            username="admin",
            success=False,
            reason="密码错误",
        )

    @pytest.mark.asyncio
    async def test_log_login_with_user_agent(self, auditor):
        """测试记录带 User-Agent 的登录"""
        await auditor.log_login(
            ip_address="192.168.1.1",
            username="admin",
            success=True,
            user_agent="Mozilla/5.0",
        )

    @pytest.mark.asyncio
    async def test_log_api_access(self, auditor):
        """测试记录 API 访问"""
        await auditor.log_api_access(
            ip_address="192.168.1.1",
            endpoint="/api/accounts",
            method="GET",
            token_prefix="abc123",
        )

    @pytest.mark.asyncio
    async def test_log_api_access_failure(self, auditor):
        """测试记录 API 访问失败"""
        await auditor.log_api_access(
            ip_address="192.168.1.1",
            endpoint="/api/accounts",
            method="GET",
            success=False,
            error_message="Unauthorized",
        )

    @pytest.mark.asyncio
    async def test_log_account_operation(self, auditor):
        """测试记录账户操作（邮件脱敏）"""
        await auditor.log_account_operation(
            event_type=AuditEventType.ACCOUNT_DELETED,
            user_id="admin",
            emails=["user1@example.com", "user2@example.com"],
            ip_address="192.168.1.1",
        )

    @pytest.mark.asyncio
    async def test_log_account_operation_many_emails(self, auditor):
        """测试记录账户操作（超过 5 个邮件）"""
        emails = [f"user{i}@example.com" for i in range(10)]
        await auditor.log_account_operation(
            event_type=AuditEventType.ACCOUNT_DELETED,
            user_id="admin",
            emails=emails,
        )

    @pytest.mark.asyncio
    async def test_log_with_details(self, auditor):
        """测试记录带详情的事件"""
        await auditor.log(
            AuditEventType.CONFIG_CHANGED,
            user_id="admin",
            ip_address="192.168.1.1",
            resource="system_config",
            action="update",
            details={"key": "session_timeout", "old_value": 3600, "new_value": 7200},
        )

    @pytest.mark.asyncio
    async def test_log_db_error_handled(self):
        """测试数据库错误被正确处理"""
        mock_db = MagicMock()
        mock_db.store_audit_event = AsyncMock(side_effect=Exception("DB Error"))
        auditor = AuditLogger(db_manager=mock_db)
        
        # 不应该抛出异常
        await auditor.log(
            AuditEventType.LOGIN_SUCCESS,
            ip_address="192.168.1.1",
        )


class TestGlobalAuditLogger:
    """全局审计日志器测试"""

    def test_audit_logger_exists(self):
        """测试全局审计日志器存在"""
        assert audit_logger is not None
        assert isinstance(audit_logger, AuditLogger)

    def test_init_audit_logger(self):
        """测试初始化审计日志器"""
        mock_db = MagicMock()
        
        # 保存原始值
        from app.core import audit
        original = audit.audit_logger
        
        try:
            init_audit_logger(mock_db)
            
            # 应该创建新的实例
            assert audit.audit_logger._db_manager == mock_db
        finally:
            # 恢复原始值
            audit.audit_logger = original
