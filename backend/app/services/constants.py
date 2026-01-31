from __future__ import annotations

from pathlib import Path
from typing import Any

from ..settings import PROJECT_ROOT, get_settings

_settings = get_settings()
DEFAULT_EMAIL_LIMIT = _settings.default_email_limit
CONFIG_MAX_EMAIL_LIMIT = _settings.max_email_limit

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
# 系统配置默认值
# ============================================================================

SYSTEM_CONFIG_DEFAULTS: dict[str, Any] = {
    "email_limit": DEFAULT_EMAIL_LIMIT,
}

# ============================================================================
# 邮件相关常量
# ============================================================================

VALID_MERGE_MODES = {"update", "skip", "replace"}
MIN_EMAIL_LIMIT = 1
MAX_EMAIL_LIMIT = CONFIG_MAX_EMAIL_LIMIT

# ============================================================================
# 认证相关常量
# ============================================================================

# Access Token 过期时间（分钟）- 建议 1-2 小时
ACCESS_TOKEN_EXPIRE_MINUTES = 60

# Refresh Token 过期时间（天）
REFRESH_TOKEN_EXPIRE_DAYS = 7

# ============================================================================
# 速率限制常量
# ============================================================================

# 登录频率限制（次数）
LOGIN_RATE_LIMIT = 5

# 登录频率限制时间窗口（秒）
LOGIN_RATE_WINDOW_SECONDS = 300

# 登录失败锁定时长（分钟）
LOGIN_LOCKOUT_MINUTES = 15

# 公共 API 速率限制（次/分钟）
PUBLIC_API_RATE_LIMIT = 60

# ============================================================================
# 分页常量
# ============================================================================

DEFAULT_PAGE_SIZE = 10
MAX_PAGE_SIZE = 100
