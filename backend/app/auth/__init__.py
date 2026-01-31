"""
认证模块
包含 OAuth2、JWT、加密安全等功能
"""

from .jwt import (
    ACCESS_TOKEN_EXPIRE_MINUTES,
    authenticate_admin,
    create_access_token,
    decode_access_token,
    get_current_admin,
    get_password_hash,
    verify_password,
)
from .oauth import get_access_token
from .security import (
    decrypt_if_needed,
    decrypt_value,
    encrypt_if_needed,
    encrypt_value,
    is_encrypted,
)

__all__ = [
    # OAuth
    "get_access_token",
    # JWT
    "create_access_token",
    "decode_access_token",
    "verify_password",
    "get_password_hash",
    "authenticate_admin",
    "get_current_admin",
    "ACCESS_TOKEN_EXPIRE_MINUTES",
    # Security
    "encrypt_value",
    "decrypt_value",
    "encrypt_if_needed",
    "decrypt_if_needed",
    "is_encrypted",
]
