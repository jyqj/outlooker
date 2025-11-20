#!/usr/bin/env python3
"""
登录频率限制器单元测试
"""

import asyncio
import pytest
from pathlib import Path

from app.rate_limiter import (
    LoginRateLimiter,
    LoginAuditor,
    MAX_LOGIN_ATTEMPTS,
    LOCKOUT_DURATION,
)


class TestLoginRateLimiter:
    """测试登录频率限制器"""

    @pytest.fixture
    def rate_limiter(self):
        """为每个测试创建新的限制器实例"""
        return LoginRateLimiter()

    @pytest.mark.asyncio
    async def test_record_failed_attempts(self, rate_limiter):
        """测试记录失败尝试"""
        ip = "192.168.1.1"
        username = "admin"
        
        # 记录几次失败
        await rate_limiter.record_attempt(ip, username, False)
        await rate_limiter.record_attempt(ip, username, False)
        
        # 获取失败次数
        count = await rate_limiter.get_attempt_count(ip, username)
        assert count == 2

    @pytest.mark.asyncio
    async def test_successful_login_clears_failures(self, rate_limiter):
        """测试成功登录清空失败记录"""
        ip = "192.168.1.2"
        username = "admin"
        
        # 先记录几次失败
        await rate_limiter.record_attempt(ip, username, False)
        await rate_limiter.record_attempt(ip, username, False)
        
        count = await rate_limiter.get_attempt_count(ip, username)
        assert count == 2
        
        # 成功登录
        await rate_limiter.record_attempt(ip, username, True)
        
        # 失败记录应该被清空
        count = await rate_limiter.get_attempt_count(ip, username)
        assert count == 0

    @pytest.mark.asyncio
    async def test_lockout_after_max_attempts(self, rate_limiter):
        """测试达到最大尝试次数后锁定"""
        ip = "192.168.1.3"
        username = "admin"
        
        # 记录 MAX_LOGIN_ATTEMPTS 次失败
        for _ in range(MAX_LOGIN_ATTEMPTS):
            await rate_limiter.record_attempt(ip, username, False)
        
        # 应该被锁定
        is_locked, remaining = await rate_limiter.is_locked_out(ip, username)
        assert is_locked is True
        assert remaining is not None
        assert remaining > 0
        assert remaining <= LOCKOUT_DURATION

    @pytest.mark.asyncio
    async def test_not_locked_before_max_attempts(self, rate_limiter):
        """测试未达到最大次数前不会锁定"""
        ip = "192.168.1.4"
        username = "admin"
        
        # 记录少于 MAX_LOGIN_ATTEMPTS 的失败
        for _ in range(MAX_LOGIN_ATTEMPTS - 1):
            await rate_limiter.record_attempt(ip, username, False)
        
        # 不应该被锁定
        is_locked, remaining = await rate_limiter.is_locked_out(ip, username)
        assert is_locked is False
        assert remaining is None

    @pytest.mark.asyncio
    async def test_lockout_expires(self, rate_limiter):
        """测试锁定过期后可以再次尝试"""
        ip = "192.168.1.5"
        username = "admin"
        
        # 触发锁定
        for _ in range(MAX_LOGIN_ATTEMPTS):
            await rate_limiter.record_attempt(ip, username, False)
        
        # 确认已锁定
        is_locked, _ = await rate_limiter.is_locked_out(ip, username)
        assert is_locked is True
        
        # 手动清除锁定（模拟时间过期）
        # 在实际场景中应该等待 LOCKOUT_DURATION 秒
        key = (ip, username)
        if key in rate_limiter._lockouts:
            rate_limiter._lockouts[key] = 0  # 设置为过期
        
        # 应该不再锁定
        is_locked, _ = await rate_limiter.is_locked_out(ip, username)
        assert is_locked is False

    @pytest.mark.asyncio
    async def test_different_ip_username_combinations(self, rate_limiter):
        """测试不同 IP 和用户名组合独立计数"""
        ip1 = "192.168.1.6"
        ip2 = "192.168.1.7"
        user1 = "admin"
        user2 = "user"
        
        # 为不同组合记录失败
        await rate_limiter.record_attempt(ip1, user1, False)
        await rate_limiter.record_attempt(ip1, user1, False)
        await rate_limiter.record_attempt(ip2, user1, False)
        await rate_limiter.record_attempt(ip1, user2, False)
        
        # 验证各自的计数
        count1 = await rate_limiter.get_attempt_count(ip1, user1)
        count2 = await rate_limiter.get_attempt_count(ip2, user1)
        count3 = await rate_limiter.get_attempt_count(ip1, user2)
        
        assert count1 == 2
        assert count2 == 1
        assert count3 == 1


class TestLoginAuditor:
    """测试登录审计日志记录器"""

    @pytest.fixture
    def auditor(self):
        """为每个测试创建新的审计器实例"""
        return LoginAuditor()

    @pytest.mark.asyncio
    async def test_log_attempt_creates_file(self, auditor, tmp_path):
        """测试日志记录会创建文件"""
        # 使用临时目录
        import app.rate_limiter as rl_module
        original_log_file = rl_module.AUDIT_LOG_FILE
        
        # 修改为临时文件
        temp_log_file = tmp_path / "test_audit.log"
        rl_module.AUDIT_LOG_FILE = temp_log_file
        auditor = LoginAuditor()  # 重新创建以使用新路径
        
        try:
            # 记录一次尝试
            await auditor.log_attempt("192.168.1.1", "admin", True)
            
            # 验证文件存在
            assert temp_log_file.exists()
            
            # 验证文件内容
            content = temp_log_file.read_text()
            assert "192.168.1.1" in content
            assert "admin" in content
        finally:
            # 恢复原始路径
            rl_module.AUDIT_LOG_FILE = original_log_file

    @pytest.mark.asyncio
    async def test_log_attempt_with_reason(self, auditor, tmp_path):
        """测试记录包含失败原因的日志"""
        import app.rate_limiter as rl_module
        original_log_file = rl_module.AUDIT_LOG_FILE
        
        temp_log_file = tmp_path / "test_audit_reason.log"
        rl_module.AUDIT_LOG_FILE = temp_log_file
        auditor = LoginAuditor()
        
        try:
            # 记录失败尝试并附带原因
            await auditor.log_attempt("192.168.1.2", "admin", False, "密码错误")
            
            content = temp_log_file.read_text()
            assert "密码错误" in content
            assert '"success": false' in content.lower()
        finally:
            rl_module.AUDIT_LOG_FILE = original_log_file


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

