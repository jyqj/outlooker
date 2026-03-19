#!/usr/bin/env python3
"""
Utilities for redacting sensitive values before they are written to logs.

新模块在记录密码、token、验证码、proof/canary 等字段时，应先调用本模块
进行脱敏，避免明文写入日志或审计明细。
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

EXACT_SECRET_KEYS = {
    "password",
    "passwd",
    "refresh_token",
    "access_token",
    "client_secret",
    "authorization",
    "cookie",
    "set_cookie",
    "set-cookie",
    "ppft",
    "sft",
    "s_ft",
    "canary",
    "api_canary",
    "apicanary",
    "proofid",
    "proof_id",
    "webhook_secret",
}

EMAIL_KEYS = {
    "email",
    "address",
    "recovery_email",
    "secondary_email",
    "new_email",
    "old_email",
}

CODE_KEYS = {
    "code",
    "otp",
    "otc",
    "verification_code",
    "iotttext",
}


def _normalize_key(key: str) -> str:
    return key.strip().lower().replace("-", "_")


def mask_secret(value: Any, prefix: int = 2, suffix: int = 2) -> str:
    """Mask a secret value while preserving a short prefix/suffix for debugging."""
    text = str(value or "")
    if not text:
        return ""
    if len(text) <= prefix + suffix:
        return "*" * len(text)
    return f"{text[:prefix]}***{text[-suffix:]}"


def mask_email(value: Any) -> str:
    """Mask the local part of an email address."""
    text = str(value or "")
    if not text or "@" not in text:
        return mask_secret(text)

    local, domain = text.split("@", 1)
    if len(local) <= 2:
        masked_local = "*" * len(local)
    else:
        masked_local = f"{local[:2]}***"
    return f"{masked_local}@{domain}"


def mask_code(value: Any) -> str:
    """Always hide the full verification code."""
    text = str(value or "")
    return "*" * len(text) if text else ""


def redact_log_data(data: Any) -> Any:
    """Recursively redact a mapping or sequence for safe logging."""
    if isinstance(data, Mapping):
        result: dict[str, Any] = {}
        for key, value in data.items():
            normalized = _normalize_key(str(key))
            if normalized in EMAIL_KEYS:
                result[str(key)] = mask_email(value)
            elif normalized in CODE_KEYS:
                result[str(key)] = mask_code(value)
            elif normalized in EXACT_SECRET_KEYS or any(
                token in normalized
                for token in ("password", "token", "secret", "canary", "proof")
            ):
                result[str(key)] = mask_secret(value)
            else:
                result[str(key)] = redact_log_data(value)
        return result

    if isinstance(data, Sequence) and not isinstance(data, (str, bytes, bytearray)):
        return [redact_log_data(item) for item in data]

    return data
