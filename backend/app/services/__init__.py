from __future__ import annotations

from ..database import db_manager
from .account_import_service import merge_accounts_data_to_db
from .account_utils import (
    _normalize_email,
    _parse_account_line,
    _validate_account_info,
    parse_account_line,
)
from .constants import SYSTEM_CONFIG_DEFAULTS, SYSTEM_CONFIG_FILE
from .email_service import EmailManager, email_manager, load_accounts_config
from .otp_service import extract_verification_code, extract_code_from_message
from .system_config_service import (
    get_system_config_value,
    load_system_config,
    set_system_config_value,
)

__all__ = [
    "EmailManager",
    "email_manager",
    "load_accounts_config",
    "merge_accounts_data_to_db",
    "load_system_config",
    "set_system_config_value",
    "get_system_config_value",
    "db_manager",
    "parse_account_line",
    "_parse_account_line",
    "_normalize_email",
    "_validate_account_info",
    "SYSTEM_CONFIG_DEFAULTS",
    "SYSTEM_CONFIG_FILE",
    "extract_verification_code",
    "extract_code_from_message",
]
