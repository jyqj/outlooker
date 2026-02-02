#!/usr/bin/env python3
"""
向后兼容模块

.. deprecated::
    此模块已废弃，请直接从 app.core 导入：
    
    - 登录相关限流器: ``from app.core.rate_limiter import rate_limiter, auditor``
    - API 限流器: ``from app.core.sliding_window_limiter import SlidingWindowRateLimiter``
    - 审计日志: ``from app.core.audit import audit_logger``
"""
import warnings

warnings.warn(
    "app.rate_limiter 模块已废弃，请使用 app.core.rate_limiter 代替。"
    "此兼容层将在未来版本中移除。",
    DeprecationWarning,
    stacklevel=2
)

from .core.rate_limiter import (
    LoginAttempt,
    LoginAuditor,
    LoginRateLimiter,
    auditor,
    public_api_rate_limiter,
    rate_limiter,
)

# 导出滑动窗口限流器
from .core.sliding_window_limiter import (
    RateLimitConfig,
    SlidingWindowRateLimiter,
)

__all__ = [
    # 登录相关
    "rate_limiter",
    "auditor",
    "LoginRateLimiter",
    "LoginAuditor",
    "LoginAttempt",
    # API 限流器
    "public_api_rate_limiter",
    "SlidingWindowRateLimiter",
    "RateLimitConfig",
]
