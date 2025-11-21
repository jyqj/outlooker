#!/usr/bin/env python3
"""
登录频率限制与审计模块

实现基于 IP 地址和用户名的登录频率限制,防止暴力破解攻击
记录所有登录尝试(成功和失败)用于安全审计
"""

import asyncio
import time
import json
from pathlib import Path
from typing import Deque, Dict, List, Optional, Tuple
from datetime import datetime
from collections import defaultdict, deque
import logging

logger = logging.getLogger(__name__)

# ============================================================================
# 配置
# ============================================================================

# 频率限制配置
MAX_LOGIN_ATTEMPTS = 5  # 最大失败次数
LOCKOUT_DURATION = 900  # 锁定时长(秒) - 15分钟
ATTEMPT_WINDOW = 300  # 统计窗口(秒) - 5分钟

# 审计日志配置
AUDIT_LOG_DIR = Path(__file__).parent / "logs"
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
    """登录频率限制器
    
    基于 IP 地址和用户名组合进行频率限制
    使用滑动窗口算法统计失败次数
    """
    
    def __init__(self):
        # 存储登录尝试: {(ip, username): [timestamps]}
        self._attempts: Dict[Tuple[str, str], List[float]] = defaultdict(list)
        # 存储锁定状态: {(ip, username): lockout_until_timestamp}
        self._lockouts: Dict[Tuple[str, str], float] = {}
        # 线程锁
        self._lock = asyncio.Lock()
    
    async def is_locked_out(self, ip: str, username: str) -> Tuple[bool, Optional[int]]:
        """检查是否被锁定
        
        Args:
            ip: 客户端 IP 地址
            username: 用户名
            
        Returns:
            (是否锁定, 剩余锁定秒数)
        """
        async with self._lock:
            key = (ip, username)
            
            if key not in self._lockouts:
                return False, None
            
            lockout_until = self._lockouts[key]
            now = time.time()
            
            if now < lockout_until:
                remaining = int(lockout_until - now)
                return True, remaining
            else:
                # 锁定已过期,清理
                del self._lockouts[key]
                return False, None
    
    async def record_attempt(self, ip: str, username: str, success: bool) -> None:
        """记录登录尝试
        
        Args:
            ip: 客户端 IP 地址
            username: 用户名
            success: 是否成功
        """
        async with self._lock:
            key = (ip, username)
            now = time.time()
            
            if success:
                # 成功登录,清除该用户的失败记录
                if key in self._attempts:
                    del self._attempts[key]
                if key in self._lockouts:
                    del self._lockouts[key]
            else:
                # 失败登录,记录时间戳
                self._attempts[key].append(now)
                
                # 清理过期的尝试记录(超出统计窗口)
                cutoff = now - ATTEMPT_WINDOW
                self._attempts[key] = [
                    ts for ts in self._attempts[key] if ts > cutoff
                ]
                
                # 检查是否超过限制
                if len(self._attempts[key]) >= MAX_LOGIN_ATTEMPTS:
                    # 触发锁定
                    self._lockouts[key] = now + LOCKOUT_DURATION
                    logger.warning(
                        f"登录频率限制触发: IP={ip}, 用户名={username}, "
                        f"失败次数={len(self._attempts[key])}, "
                        f"锁定时长={LOCKOUT_DURATION}秒"
                    )
    
    async def get_attempt_count(self, ip: str, username: str) -> int:
        """获取当前失败尝试次数
        
        Args:
            ip: 客户端 IP 地址
            username: 用户名
            
        Returns:
            当前窗口内的失败次数
        """
        async with self._lock:
            key = (ip, username)
            if key not in self._attempts:
                return 0
            
            # 清理过期记录
            now = time.time()
            cutoff = now - ATTEMPT_WINDOW
            self._attempts[key] = [
                ts for ts in self._attempts[key] if ts > cutoff
            ]
            
            return len(self._attempts[key])


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
        reason: Optional[str] = None
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
        self._records: Dict[str, Deque[float]] = defaultdict(deque)
        self._lock = asyncio.Lock()

    async def is_allowed(self, key: str) -> Tuple[bool, Optional[int]]:
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
