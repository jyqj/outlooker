#!/usr/bin/env python3
"""
登录频率限制模块

实现基于 IP 地址和用户名的登录频率限制,防止暴力破解攻击
审计日志功能已统一到 core/audit.py 的 AuditLogger
"""

import asyncio
import logging
from datetime import datetime, timedelta
from pathlib import Path

logger = logging.getLogger(__name__)
from ..db import db_manager
from ..settings import get_settings

# ============================================================================
# 配置
# ============================================================================

settings = get_settings()

# 频率限制配置（从 settings 读取，支持环境变量覆盖）
MAX_LOGIN_ATTEMPTS = settings.max_login_attempts
LOCKOUT_DURATION = settings.lockout_duration_seconds
ATTEMPT_WINDOW = settings.login_attempt_window_seconds

# 审计日志配置（向后兼容，实际审计已统一到 AuditLogger）
AUDIT_LOG_DIR = Path(settings.logs_dir)
AUDIT_LOG_FILE = AUDIT_LOG_DIR / "login_audit.log"


# ============================================================================
# 数据结构（向后兼容）
# ============================================================================

class LoginAttempt:
    """登录尝试记录（向后兼容，新代码请使用 AuditEvent）"""
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
# 审计日志（委托给 AuditLogger）
# ============================================================================

class LoginAuditor:
    """登录审计日志记录器
    
    已重构为 AuditLogger 的适配器，保持向后兼容。
    新代码请直接使用 audit_logger.log_login()。
    """

    def __init__(self):
        # 确保日志目录存在（向后兼容）
        AUDIT_LOG_DIR.mkdir(parents=True, exist_ok=True)

    async def log_attempt(
        self,
        ip: str,
        username: str,
        success: bool,
        reason: str | None = None
    ) -> None:
        """记录登录尝试到审计日志
        
        现已委托给 AuditLogger 统一处理。
        
        Args:
            ip: 客户端 IP 地址
            username: 用户名
            success: 是否成功
            reason: 失败原因(可选)
        """
        # 延迟导入避免循环依赖
        from .audit import audit_logger
        
        await audit_logger.log_login(
            ip_address=ip,
            username=username,
            success=success,
            reason=reason,
        )


# ============================================================================
# 全局实例
# ============================================================================

rate_limiter = LoginRateLimiter()
auditor = LoginAuditor()

# 公共 API 限流器：直接使用 SlidingWindowRateLimiter
# 已移除废弃的 RequestRateLimiter 和代理类
# 推荐使用 sliding_window_limiter 模块中的 public_api_limiter
from .sliding_window_limiter import public_api_limiter as public_api_rate_limiter
