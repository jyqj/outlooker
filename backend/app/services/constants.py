"""
常量定义模块

所有常量均从配置系统读取，支持环境变量覆盖。
保持向后兼容性，现有代码可继续使用这些常量。

使用方式：
    from .constants import DEFAULT_EMAIL_LIMIT, MAX_EMAIL_LIMIT
    
或通过配置系统直接访问：
    from ..settings import get_settings
    settings = get_settings()
    settings.email.default_limit  # 分组访问
    settings.default_email_limit  # 平坦访问（向后兼容）
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from ..settings import PROJECT_ROOT, get_settings

_settings = get_settings()

# ============================================================================
# 文件路径常量
# ============================================================================

CONFIG_DIR = PROJECT_ROOT / "backend" / "configs"
CONFIG_DIR.mkdir(parents=True, exist_ok=True)

ACCOUNTS_CONFIG_FILES: list[Path] = [
    CONFIG_DIR / "config.txt",
    CONFIG_DIR / "accounts.txt",
]

SYSTEM_CONFIG_FILE = CONFIG_DIR / "system_config.json"
SYSTEM_CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)

# ============================================================================
# 邮件相关常量（从配置系统读取）
# ============================================================================

DEFAULT_EMAIL_LIMIT = _settings.email.default_limit
MAX_EMAIL_LIMIT = _settings.email.max_limit
MIN_EMAIL_LIMIT = _settings.email.min_limit

VALID_MERGE_MODES = {"update", "skip", "replace"}

# ============================================================================
# 系统配置默认值
# ============================================================================

SYSTEM_CONFIG_DEFAULTS: dict[str, Any] = {
    "email_limit": DEFAULT_EMAIL_LIMIT,
}

# ============================================================================
# 认证相关常量（从配置系统读取）
# ============================================================================

ACCESS_TOKEN_EXPIRE_MINUTES = _settings.auth.access_token_expire_minutes
REFRESH_TOKEN_EXPIRE_DAYS = _settings.auth.refresh_token_expire_days

# ============================================================================
# 速率限制常量（从配置系统读取）
# ============================================================================

LOGIN_RATE_LIMIT = _settings.rate_limit.max_login_attempts
LOGIN_RATE_WINDOW_SECONDS = _settings.rate_limit.login_attempt_window_seconds
LOGIN_LOCKOUT_MINUTES = _settings.rate_limit.lockout_duration_seconds // 60
PUBLIC_API_RATE_LIMIT = _settings.rate_limit.public_api_rate_limit

# ============================================================================
# 分页常量（从配置系统读取）
# ============================================================================

DEFAULT_PAGE_SIZE = _settings.pagination.default_page_size
MAX_PAGE_SIZE = _settings.pagination.max_page_size
