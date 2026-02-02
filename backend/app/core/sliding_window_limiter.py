#!/usr/bin/env python3
"""
Sliding window rate limiter implementation.
"""

import asyncio
import time
from dataclasses import dataclass
from typing import Tuple

from fastapi import HTTPException, Request, status

from .audit import AuditEventType, audit_logger


@dataclass
class RateLimitConfig:
    """速率限制配置"""
    max_requests: int  # 窗口内最大请求数
    window_seconds: int  # 窗口大小（秒）


class SlidingWindowRateLimiter:
    """滑动窗口速率限制器（带内存保护）"""
    
    def __init__(self, config: RateLimitConfig, max_tracked_keys: int | None = None):
        self.config = config
        self._windows: dict[str, list[float]] = {}  # 不用 defaultdict
        self._lock = asyncio.Lock()
        self._max_tracked_keys = max_tracked_keys
    
    @property
    def max_tracked_keys(self) -> int:
        """延迟获取 max_tracked_keys，避免循环导入"""
        if self._max_tracked_keys is not None:
            return self._max_tracked_keys
        # 延迟导入避免循环依赖
        from ..settings import get_settings
        return get_settings().max_tracked_keys
    
    async def is_allowed(self, key: str) -> Tuple[bool, int]:
        """
        检查请求是否允许。
        
        Args:
            key: 限制键（如 IP 地址或 token）
            
        Returns:
            (是否允许, 剩余配额)
        """
        async with self._lock:
            now = time.time()
            window_start = now - self.config.window_seconds
            
            # 内存保护：如果键数量过多，先清理
            if len(self._windows) >= self.max_tracked_keys:
                await self._cleanup_expired_unlocked(window_start)
                
                # 如果仍然过多，删除最旧的
                if len(self._windows) >= self.max_tracked_keys:
                    self._evict_oldest()
            
            # 获取或创建窗口
            if key not in self._windows:
                self._windows[key] = []
            
            # 清理过期记录
            self._windows[key] = [
                ts for ts in self._windows[key] if ts > window_start
            ]
            
            # 检查是否超限
            current_count = len(self._windows[key])
            remaining = max(0, self.config.max_requests - current_count)
            
            if current_count >= self.config.max_requests:
                return False, 0
            
            # 记录本次请求
            self._windows[key].append(now)
            return True, remaining - 1
    
    def _evict_oldest(self) -> None:
        """淘汰最旧的键"""
        if not self._windows:
            return
        
        # 找到最旧的键（最小时间戳）
        oldest_key = min(
            self._windows.keys(),
            key=lambda k: min(self._windows[k]) if self._windows[k] else 0
        )
        del self._windows[oldest_key]
    
    async def _cleanup_expired_unlocked(self, window_start: float) -> None:
        """清理过期记录（不获取锁，由调用者保证）"""
        keys_to_delete = []
        for key in self._windows:
            self._windows[key] = [
                ts for ts in self._windows[key] if ts > window_start
            ]
            if not self._windows[key]:
                keys_to_delete.append(key)
        
        for key in keys_to_delete:
            del self._windows[key]
    
    async def get_remaining(self, key: str) -> int:
        """获取剩余配额"""
        async with self._lock:
            now = time.time()
            window_start = now - self.config.window_seconds
            
            valid_requests = [
                ts for ts in self._windows.get(key, []) if ts > window_start
            ]
            return max(0, self.config.max_requests - len(valid_requests))
    
    async def reset(self, key: str) -> None:
        """重置指定键的限制"""
        async with self._lock:
            self._windows.pop(key, None)
    
    async def cleanup_expired(self) -> int:
        """清理所有过期记录"""
        async with self._lock:
            now = time.time()
            window_start = now - self.config.window_seconds
            cleaned = 0
            
            for key in list(self._windows.keys()):
                original_len = len(self._windows[key])
                self._windows[key] = [
                    ts for ts in self._windows[key] if ts > window_start
                ]
                cleaned += original_len - len(self._windows[key])
                
                # 删除空列表
                if not self._windows[key]:
                    del self._windows[key]
            
            return cleaned


# 公共 API 限流器（默认：每分钟 60 次请求）
public_api_limiter = SlidingWindowRateLimiter(
    RateLimitConfig(max_requests=60, window_seconds=60)
)

# 登录限流器（默认：每 5 分钟 5 次失败）
login_limiter = SlidingWindowRateLimiter(
    RateLimitConfig(max_requests=5, window_seconds=300)
)


async def check_public_api_rate_limit(request: Request) -> None:
    """
    公共 API 速率限制检查。
    
    作为 FastAPI 依赖使用：
    
    ```python
    @router.get("/endpoint")
    async def endpoint(
        request: Request,
        _: None = Depends(check_public_api_rate_limit),
    ):
        ...
    ```
    """
    client_ip = request.client.host if request.client else "unknown"
    
    allowed, remaining = await public_api_limiter.is_allowed(client_ip)
    
    if not allowed:
        # 记录超限事件
        await audit_logger.log(
            AuditEventType.RATE_LIMIT_EXCEEDED,
            ip_address=client_ip,
            resource=str(request.url.path),
            action=request.method,
            success=False,
            error_message="Rate limit exceeded",
        )
        
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many requests. Please try again later.",
            headers={"Retry-After": "60"},
        )


async def check_login_rate_limit(request: Request, username: str) -> None:
    """
    登录速率限制检查。
    
    基于 IP + 用户名组合进行限制。
    """
    client_ip = request.client.host if request.client else "unknown"
    key = f"{client_ip}:{username}"
    
    allowed, remaining = await login_limiter.is_allowed(key)
    
    if not allowed:
        # 记录超限事件
        await audit_logger.log(
            AuditEventType.RATE_LIMIT_EXCEEDED,
            ip_address=client_ip,
            resource="auth/login",
            action="POST",
            details={"username": username},
            success=False,
            error_message="Login rate limit exceeded",
        )
        
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many login attempts. Please try again in 5 minutes.",
            headers={"Retry-After": "300"},
        )
