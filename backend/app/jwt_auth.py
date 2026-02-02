#!/usr/bin/env python3
"""向后兼容模块：请使用 app.auth.jwt"""

import warnings

warnings.warn(
    "app.jwt_auth 模块已废弃，请使用 app.auth.jwt 代替。"
    "此兼容层将在未来版本中移除。",
    DeprecationWarning,
    stacklevel=2
)

from .auth.jwt import (
    authenticate_admin,
    create_access_token,
    decode_access_token,
    get_current_admin,
    get_password_hash,
    verify_password,
)

__all__ = [
    "create_access_token",
    "decode_access_token",
    "authenticate_admin",
    "get_current_admin",
    "get_password_hash",
    "verify_password",
]
