"""Verification code provider abstractions for protocol flows."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Awaitable, Callable


@dataclass
class CodeFetchResult:
    code: str
    email_id: int | None = None
    source: str = "unknown"


class ProtocolCodeProvider:
    """Abstract protocol verification code provider."""

    async def fetch_code(
        self,
        address: str,
        *,
        min_email_id: int | None = None,
        timeout: int = 150,
        poll_interval: int = 5,
    ) -> CodeFetchResult:
        raise NotImplementedError


class CallbackCodeProvider(ProtocolCodeProvider):
    """Adapter around an async callback returning a code or a CodeFetchResult."""

    def __init__(self, callback: Callable[..., Awaitable[CodeFetchResult | str]]):
        self.callback = callback

    async def fetch_code(
        self,
        address: str,
        *,
        min_email_id: int | None = None,
        timeout: int = 150,
        poll_interval: int = 5,
    ) -> CodeFetchResult:
        result = await self.callback(
            address=address,
            min_email_id=min_email_id,
            timeout=timeout,
            poll_interval=poll_interval,
        )
        if isinstance(result, CodeFetchResult):
            return result
        return CodeFetchResult(code=str(result), email_id=min_email_id, source="callback")


class StaticCodeProvider(ProtocolCodeProvider):
    """Simple provider for tests and manual flows."""

    def __init__(self, code: str):
        self.code = code

    async def fetch_code(
        self,
        address: str,
        *,
        min_email_id: int | None = None,
        timeout: int = 150,
        poll_interval: int = 5,
    ) -> CodeFetchResult:
        await asyncio.sleep(0)
        return CodeFetchResult(code=self.code, email_id=min_email_id, source="static")
