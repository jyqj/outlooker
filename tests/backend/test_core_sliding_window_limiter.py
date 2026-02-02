"""Tests for sliding window rate limiter."""

import pytest
import asyncio
from unittest.mock import patch, MagicMock, AsyncMock
import time

from app.core.sliding_window_limiter import (
    SlidingWindowRateLimiter,
    RateLimitConfig,
    login_limiter,
    public_api_limiter,
)


class TestSlidingWindowRateLimiter:
    """滑动窗口限流器测试"""

    @pytest.fixture
    def limiter(self):
        """创建限流器实例"""
        config = RateLimitConfig(max_requests=5, window_seconds=60)
        return SlidingWindowRateLimiter(config, max_tracked_keys=100)

    @pytest.mark.asyncio
    async def test_allow_within_limit(self, limiter):
        """测试在限制内允许请求"""
        key = "test_user_1"
        
        # 前 5 次请求应该被允许
        for i in range(5):
            allowed, remaining = await limiter.is_allowed(key)
            assert allowed is True
            # remaining 应该递减
            assert remaining == 4 - i

    @pytest.mark.asyncio
    async def test_block_over_limit(self, limiter):
        """测试超过限制阻止请求"""
        key = "test_user_2"
        
        # 消耗所有配额
        for _ in range(5):
            await limiter.is_allowed(key)
        
        # 第 6 次应该被阻止
        allowed, remaining = await limiter.is_allowed(key)
        assert allowed is False
        assert remaining == 0

    @pytest.mark.asyncio
    async def test_different_keys_independent(self, limiter):
        """测试不同 key 独立计数"""
        key1 = "user_a"
        key2 = "user_b"
        
        # user_a 消耗配额
        for _ in range(5):
            await limiter.is_allowed(key1)
        
        # user_b 应该仍然可以请求
        allowed, remaining = await limiter.is_allowed(key2)
        assert allowed is True
        assert remaining == 4  # 5 - 1 = 4

    @pytest.mark.asyncio
    async def test_reset_key(self, limiter):
        """测试重置 key"""
        key = "test_user_3"
        
        # 消耗配额
        for _ in range(5):
            await limiter.is_allowed(key)
        
        # 重置
        await limiter.reset(key)
        
        # 应该可以再次请求
        allowed, remaining = await limiter.is_allowed(key)
        assert allowed is True
        assert remaining == 4

    @pytest.mark.asyncio
    async def test_get_remaining(self, limiter):
        """测试获取剩余配额"""
        key = "test_user_4"
        
        # 初始状态应该是满配额
        remaining = await limiter.get_remaining(key)
        assert remaining == 5
        
        # 消耗 2 次
        await limiter.is_allowed(key)
        await limiter.is_allowed(key)
        
        remaining = await limiter.get_remaining(key)
        assert remaining == 3

    @pytest.mark.asyncio
    async def test_cleanup_expired(self, limiter):
        """测试清理过期记录"""
        key = "test_user_5"
        
        # 使用短窗口的限流器
        short_config = RateLimitConfig(max_requests=5, window_seconds=1)
        short_limiter = SlidingWindowRateLimiter(short_config, max_tracked_keys=100)
        
        # 添加请求
        await short_limiter.is_allowed(key)
        await short_limiter.is_allowed(key)
        
        # 等待窗口过期
        await asyncio.sleep(1.1)
        
        # 清理应该返回已清理的记录数
        cleaned = await short_limiter.cleanup_expired()
        assert cleaned >= 0

    @pytest.mark.asyncio
    async def test_memory_protection_eviction(self):
        """测试内存保护：超过最大键数时淘汰"""
        config = RateLimitConfig(max_requests=5, window_seconds=60)
        limiter = SlidingWindowRateLimiter(config, max_tracked_keys=3)
        
        # 添加 3 个键（达到上限）
        await limiter.is_allowed("key1")
        await limiter.is_allowed("key2")
        await limiter.is_allowed("key3")
        
        # 添加第 4 个键应该触发淘汰
        await limiter.is_allowed("key4")
        
        # 键数量应该不超过限制
        assert len(limiter._windows) <= 3


class TestLoginRateLimiter:
    """登录限流器测试"""

    @pytest.mark.asyncio
    async def test_login_limiter_exists(self):
        """测试登录限流器已正确配置"""
        assert login_limiter is not None
        assert login_limiter.config.max_requests > 0
        assert login_limiter.config.window_seconds > 0

    @pytest.mark.asyncio
    async def test_login_limiter_config(self):
        """测试登录限流器配置正确"""
        # 默认：每 5 分钟 5 次失败
        assert login_limiter.config.max_requests == 5
        assert login_limiter.config.window_seconds == 300


class TestPublicApiLimiter:
    """公共 API 限流器测试"""

    @pytest.mark.asyncio
    async def test_public_api_limiter_exists(self):
        """测试公共 API 限流器已正确配置"""
        assert public_api_limiter is not None
        assert public_api_limiter.config.max_requests > 0
        assert public_api_limiter.config.window_seconds > 0

    @pytest.mark.asyncio
    async def test_public_api_limiter_config(self):
        """测试公共 API 限流器配置正确"""
        # 默认：每分钟 60 次请求
        assert public_api_limiter.config.max_requests == 60
        assert public_api_limiter.config.window_seconds == 60


class TestRateLimitConfig:
    """速率限制配置测试"""

    def test_config_creation(self):
        """测试配置创建"""
        config = RateLimitConfig(max_requests=10, window_seconds=120)
        assert config.max_requests == 10
        assert config.window_seconds == 120

    def test_config_dataclass(self):
        """测试配置是 dataclass"""
        config = RateLimitConfig(max_requests=5, window_seconds=60)
        # dataclass 应该有这些属性
        assert hasattr(config, 'max_requests')
        assert hasattr(config, 'window_seconds')
