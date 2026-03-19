"""Schemas for channel management APIs."""

from __future__ import annotations

from pydantic import BaseModel


class ChannelCreateRequest(BaseModel):
    code: str
    name: str
    status: str = "active"
    priority: int = 0
    pick_strategy: str = "round_robin"
    cooldown_seconds: int = 0
    proxy_url: str = ""
    proxy_group: str = ""
    notes: str = ""


class ChannelUpdateRequest(BaseModel):
    code: str | None = None
    name: str | None = None
    status: str | None = None
    priority: int | None = None
    pick_strategy: str | None = None
    cooldown_seconds: int | None = None
    proxy_url: str | None = None
    proxy_group: str | None = None
    notes: str | None = None


class ChannelBindAccountsRequest(BaseModel):
    emails: list[str]
    status: str = "active"
    weight: int = 100


class ChannelBindResourcesRequest(BaseModel):
    resource_ids: list[int]
    status: str = "active"
