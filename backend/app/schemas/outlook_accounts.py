"""Schemas for Outlook account management APIs."""

from __future__ import annotations

from typing import Annotated, Any

from pydantic import BaseModel, Field

BatchEmail = Annotated[str, Field(min_length=3, max_length=320)]


class BatchRefreshRequest(BaseModel):
    emails: list[BatchEmail] = Field(default_factory=list, max_length=200)
    limit: int = Field(default=100, ge=1, le=200)
    offset: int = Field(default=0, ge=0)
    concurrency: int = Field(default=5, ge=1, le=20)


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
