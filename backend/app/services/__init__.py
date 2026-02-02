from __future__ import annotations

from ..db import db_manager
from .account_cache_service import AccountCacheService, account_cache
from .account_import_service import merge_accounts_data_to_db
from .account_utils import (
    _normalize_email,
    _parse_account_line,
    _validate_account_info,
    parse_account_line,
)
from .admin_service import AdminAuthService, admin_auth_service
from .cache_warmup_service import (
    CacheWarmupService,
    cache_warmup_service,
    schedule_cache_warmup,
)
from .constants import SYSTEM_CONFIG_DEFAULTS, SYSTEM_CONFIG_FILE
from .email_fetch_service import EmailFetchService, email_fetch_service
from .email_service import EmailManager, email_manager, load_accounts_config
from .imap_client_pool import IMAPClientPool, imap_pool
from .otp_service import extract_code_from_message, extract_verification_code
from .system_config_service import (
    get_system_config_value,
    load_system_config,
    set_system_config_value,
)

__all__ = [
    # Email 管理（门面）
    "EmailManager",
    "email_manager",
    "load_accounts_config",
    # 账户缓存服务
    "AccountCacheService",
    "account_cache",
    # IMAP 客户端池
    "IMAPClientPool",
    "imap_pool",
    # 邮件获取服务
    "EmailFetchService",
    "email_fetch_service",
    # 账户导入
    "merge_accounts_data_to_db",
    # 系统配置
    "load_system_config",
    "set_system_config_value",
    "get_system_config_value",
    # 数据库管理
    "db_manager",
    # 账户工具
    "parse_account_line",
    "_parse_account_line",
    "_normalize_email",
    "_validate_account_info",
    # 常量
    "SYSTEM_CONFIG_DEFAULTS",
    "SYSTEM_CONFIG_FILE",
    # OTP 服务
    "extract_verification_code",
    "extract_code_from_message",
    # 管理员认证
    "admin_auth_service",
    "AdminAuthService",
    # 缓存预热服务
    "CacheWarmupService",
    "cache_warmup_service",
    "schedule_cache_warmup",
]
