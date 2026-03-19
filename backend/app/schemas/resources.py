"""Schemas for auxiliary resource management APIs."""

from __future__ import annotations

from pydantic import BaseModel, Field


class AuxEmailResourceCreateRequest(BaseModel):
    address: str
    provider: str = "custom"
    source_type: str = "manual"
    status: str = "available"
    channel_id: int | None = None
    notes: str = ""


class AuxEmailResourceBatchImportRequest(BaseModel):
    items: list[AuxEmailResourceCreateRequest] = Field(default_factory=list)


class AuxEmailResourceUpdateRequest(BaseModel):
    provider: str | None = None
    source_type: str | None = None
    status: str | None = None
    channel_id: int | None = None
    fail_count: int | None = None
    last_email_id: int | None = None
    bound_account_email: str | None = None
    notes: str | None = None


class AuxEmailResourceRotateRequest(BaseModel):
    replacement_address: str | None = None
    max_fail_count: int = 2
    reason: str = ""
