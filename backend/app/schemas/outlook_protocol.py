"""Schemas for single-run Outlook protocol operations."""

from __future__ import annotations

from pydantic import BaseModel


class ProtocolLoginRequest(BaseModel):
    email: str
    password: str
    channel_id: int | None = None


class ProtocolListProofsRequest(ProtocolLoginRequest):
    pass


class ProtocolBindRequest(ProtocolLoginRequest):
    recovery_email: str
    verification_email: str | None = None
    static_code: str
    queue: bool = False


class ProtocolReplaceRequest(ProtocolLoginRequest):
    old_email: str
    new_email: str
    verification_email: str | None = None
    static_code: str
    queue: bool = False
