"""Secret-free OAuth token response projections."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

_PUBLIC_TOKEN_FIELDS = (
    "id",
    "oauth_config_id",
    "email",
    "expires_at",
    "scopes_granted",
    "status",
    "last_error",
    "created_at",
    "updated_at",
)


def to_public_oauth_token(token: Mapping[str, Any] | None) -> dict[str, Any] | None:
    """Return operational token metadata without bearer or refresh credentials."""
    if token is None:
        return None

    public = {field: token.get(field) for field in _PUBLIC_TOKEN_FIELDS}
    public["has_access_token"] = bool(
        token.get("has_access_token", token.get("access_token"))
    )
    public["has_refresh_token"] = bool(
        token.get("has_refresh_token", token.get("refresh_token"))
    )
    return public
