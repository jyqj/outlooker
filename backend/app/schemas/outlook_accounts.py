"""Schemas for Outlook account management APIs."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class BatchRefreshRequest(BaseModel):
    emails: list[str] = Field(default_factory=list)
    limit: int = 100
    offset: int = 0
    concurrency: int = 5


class ProfileUpdateRequest(BaseModel):
    updates: dict[str, Any] = Field(default_factory=dict)


class PasswordChangeRequest(BaseModel):
    current_password: str
    new_password: str


class EmailAuthMethodCreateRequest(BaseModel):
    recovery_email: str


class EmailAuthMethodUpdateRequest(BaseModel):
    new_email: str


class PhoneAuthMethodCreateRequest(BaseModel):
    phone_number: str
    phone_type: str = "mobile"


class RiskDismissRequest(BaseModel):
    user_id: str


class RegionalSettingsUpdateRequest(BaseModel):
    updates: dict[str, Any] = Field(default_factory=dict)


class MailboxSettingsUpdateRequest(BaseModel):
    updates: dict[str, Any] = Field(default_factory=dict)
