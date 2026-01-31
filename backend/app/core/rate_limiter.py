#!/usr/bin/env python3
"""
登录频率限制与审计模块

实现基于 IP 地址和用户名的登录频率限制,防止暴力破解攻击
记录所有登录尝试(成功和失败)用于安全审计
"""

import asyncio
import json
import logging
import time
from collections import defaultdict, deque
from datetime import datetime, timedelta
from pathlib import Path

logger = logging.getLogger(__name__)
from ..database import db_manager
from ..settings import get_settings

# ============================================================================
# 配置
# ============================================================================

settings = get_settings()

# 频率限制配置（从 settings 读取，支持环境变量覆盖）
MAX_LOGIN_ATTEMPTS = settings.max_login_attempts
LOCKOUT_DURATION = settings.lockout_duration_seconds
ATTEMPT_WINDOW = settings.login_attempt_window_seconds

# 审计日志配置
AUDIT_LOG_DIR = Path(settings.logs_dir)
AUDIT_LOG_FILE = AUDIT_LOG_DIR / "login_audit.log"


# ============================================================================
# 数据结构
# ============================================================================

class LoginAttempt:
    """登录尝试记录"""
    def __init__(self, ip: str, username: str, success: bool, timestamp: float):
        self.ip = ip
        self.username = username
        self.success = success
        self.timestamp = timestamp

    def to_dict(self) -> dict:
        return {
            "ip": self.ip,
            "username": self.username,
            "success": self.success,
            "timestamp": self.timestamp,
            "datetime": datetime.fromtimestamp(self.timestamp).isoformat()
        }


# ============================================================================
# 频率限制器
# ============================================================================

class LoginRateLimiter:
    """登录频率限制器，持久化存储于 SQLite"""

    def __init__(self):
        self._lock = asyncio.Lock()

    async def is_locked_out(self, ip: str, username: str) -> tuple[bool, int | None]:
        async with self._lock:
            lockout_until = await db_manager.get_lockout(ip, username)
            if not lockout_until:
                return False, None
            now = datetime.utcnow()
            if lockout_until > now:
                remaining = int((lockout_until - now).total_seconds())
                return True, max(remaining, 1)
            return False, None

    async def record_attempt(self, ip: str, username: str, success: bool) -> None:
        async with self._lock:
            await db_manager.record_login_attempt(ip, username, success)
            if success:
                await db_manager.clear_lockout(ip, username)
                return

            failures = await db_manager.count_recent_failures(ip, username, ATTEMPT_WINDOW)
            if failures >= MAX_LOGIN_ATTEMPTS:
                lockout_until = datetime.utcnow() + timedelta(seconds=LOCKOUT_DURATION)
                await db_manager.set_lockout(ip, username, lockout_until)
                logger.warning(
                    "登录频率限制触发: IP=%s, 用户名=%s, 失败次数=%s, 锁定时长=%s秒",
                    ip,
                    username,
                    failures,
                    LOCKOUT_DURATION,
                )

    async def get_attempt_count(self, ip: str, username: str) -> int:
        async with self._lock:
            return await db_manager.count_recent_failures(ip, username, ATTEMPT_WINDOW)


# ============================================================================
# 审计日志
# ============================================================================

class LoginAuditor:
    """登录审计日志记录器"""

    def __init__(self):
        # 确保日志目录存在
        AUDIT_LOG_DIR.mkdir(parents=True, exist_ok=True)
        self._lock = asyncio.Lock()

    async def log_attempt(
        self,
        ip: str,
        username: str,
        success: bool,
        reason: str | None = None
    ) -> None:
        """记录登录尝试到审计日志
        
        Args:
            ip: 客户端 IP 地址
            username: 用户名
            success: 是否成功
            reason: 失败原因(可选)
        """
        async with self._lock:
            attempt = LoginAttempt(ip, username, success, time.time())
            log_entry = attempt.to_dict()

            if reason:
                log_entry["reason"] = reason

            try:
                # 追加到审计日志文件
                with AUDIT_LOG_FILE.open("a", encoding="utf-8") as f:
                    f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")
            except Exception as e:
                logger.error(f"写入审计日志失败: {e}")


# ============================================================================
# 全局实例
# ============================================================================

rate_limiter = LoginRateLimiter()
auditor = LoginAuditor()


class RequestRateLimiter:
    """用于 API 的简单按 IP 频率限制器"""

    def __init__(self, max_requests: int, window_seconds: int):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._records: dict[str, deque[float]] = defaultdict(deque)
        self._lock = asyncio.Lock()

    async def is_allowed(self, key: str) -> tuple[bool, int | None]:
        """返回是否允许请求以及建议的重试秒数"""
        async with self._lock:
            now = time.time()
            window_start = now - self.window_seconds
            hits = self._records[key]

            while hits and hits[0] <= window_start:
                hits.popleft()

            if len(hits) >= self.max_requests:
                retry_after = int(self.window_seconds - (now - hits[0]))
                return False, max(retry_after, 1)

            hits.append(now)
            return True, None


# 公共 API 的缺省限流：每分钟最多 60 次
public_api_rate_limiter = RequestRateLimiter(max_requests=60, window_seconds=60)
