#!/usr/bin/env python3
"""向后兼容的配置入口，内部使用 Settings 对象。"""

import logging

from .settings import get_settings

settings = get_settings()

# OAuth / IMAP
CLIENT_ID = settings.client_id
TOKEN_URL = settings.token_url
IMAP_SERVER = settings.imap_server
IMAP_PORT = settings.imap_port
INBOX_FOLDER_NAME = settings.inbox_folder_name
JUNK_FOLDER_NAME = settings.junk_folder_name

# 管理认证配置
LEGACY_ADMIN_TOKEN = settings.legacy_admin_token
ENABLE_LEGACY_ADMIN_TOKEN = settings.enable_legacy_admin_token

# CORS / 系统配置
ALLOWED_ORIGINS = settings.allowed_origins
DEFAULT_EMAIL_LIMIT = settings.default_email_limit
MAX_EMAIL_LIMIT = settings.max_email_limit

# 其他
LOG_LEVEL = settings.log_level

logging.basicConfig(level=LOG_LEVEL)
logger = logging.getLogger("OutlookManager")
