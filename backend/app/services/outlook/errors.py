"""Shared exceptions for Outlook Graph and protocol services."""

from __future__ import annotations

from typing import Any


class GraphAPIError(Exception):
    """Normalized Graph API error."""

    def __init__(self, status: int, message: str, code: str = ""):
        self.status = status
        self.message = message
        self.code = code
        super().__init__(f"Graph API error {status}: {code or 'UNKNOWN'} - {message}")


class OutlookProtocolError(Exception):
    """Protocol-flow exception with optional context payload."""

    def __init__(self, message: str, context: dict[str, Any] | None = None):
        self.message = message
        self.context = context or {}
        super().__init__(message)
