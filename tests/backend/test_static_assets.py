"""Tests for static asset resolution and cache policy."""

import pytest

from app.core.static_assets import (
    HTML_CACHE_CONTROL,
    IMMUTABLE_ASSET_CACHE_CONTROL,
    STATIC_ASSET_CACHE_CONTROL,
    StaticAssetCacheMiddleware,
    cache_control_for_path,
    resolve_static_asset,
)


def test_resolve_static_asset_serves_vite_public_files(tmp_path):
    favicon = tmp_path / "favicon.svg"
    favicon.write_text("<svg />", encoding="utf-8")

    assert resolve_static_asset(tmp_path, "favicon.svg") == favicon.resolve()
    assert resolve_static_asset(tmp_path, "/favicon.svg") == favicon.resolve()


def test_resolve_static_asset_rejects_traversal_and_missing_files(tmp_path):
    outside = tmp_path.parent / "secret.txt"
    outside.write_text("secret", encoding="utf-8")

    assert resolve_static_asset(tmp_path, "../secret.txt") is None
    assert resolve_static_asset(tmp_path, "missing.svg") is None


def test_cache_policy_distinguishes_documents_and_hashed_assets():
    assert cache_control_for_path("/", "text/html; charset=utf-8") == HTML_CACHE_CONTROL
    assert cache_control_for_path("/index.html") == HTML_CACHE_CONTROL
    assert (
        cache_control_for_path("/assets/app-3f91ad2.js", "text/javascript")
        == IMMUTABLE_ASSET_CACHE_CONTROL
    )
    assert cache_control_for_path("/favicon.svg", "image/svg+xml") == STATIC_ASSET_CACHE_CONTROL
    assert cache_control_for_path("/api/health/live", "application/json") is None
    assert cache_control_for_path("/openapi.json", "application/json") is None


async def _run_cache_middleware(path: str, status: int) -> list[dict]:
    async def application(scope, receive, send):
        await send(
            {
                "type": "http.response.start",
                "status": status,
                "headers": [(b"content-type", b"application/javascript")],
            }
        )
        await send({"type": "http.response.body", "body": b""})

    messages: list[dict] = []

    async def receive():
        return {"type": "http.request"}

    async def send(message):
        messages.append(message)

    middleware = StaticAssetCacheMiddleware(application)
    await middleware({"type": "http", "path": path}, receive, send)
    return messages


@pytest.mark.asyncio
async def test_cache_middleware_does_not_make_missing_assets_immutable():
    success = await _run_cache_middleware("/assets/app-hash.js", 200)
    missing = await _run_cache_middleware("/assets/missing.js", 404)

    success_headers = dict(success[0]["headers"])
    missing_headers = dict(missing[0]["headers"])
    assert success_headers[b"cache-control"] == IMMUTABLE_ASSET_CACHE_CONTROL.encode()
    assert b"cache-control" not in missing_headers
