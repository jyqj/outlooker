"""Static asset resolution and HTTP cache policy helpers."""

from pathlib import Path, PurePosixPath

from starlette.datastructures import MutableHeaders
from starlette.types import ASGIApp, Message, Receive, Scope, Send

IMMUTABLE_ASSET_CACHE_CONTROL = "public, max-age=31536000, immutable"
STATIC_ASSET_CACHE_CONTROL = "public, max-age=3600, stale-while-revalidate=86400"
HTML_CACHE_CONTROL = "no-cache"

_STATIC_SUFFIXES = frozenset(
    {
        ".avif",
        ".css",
        ".gif",
        ".ico",
        ".jpeg",
        ".jpg",
        ".js",
        ".json",
        ".map",
        ".mjs",
        ".otf",
        ".png",
        ".svg",
        ".ttf",
        ".webp",
        ".woff",
        ".woff2",
    }
)


def cache_control_for_path(path: str, content_type: str | None = None) -> str | None:
    """Return the cache policy for a response path and content type."""
    normalized_path = path.lower()
    normalized_content_type = (content_type or "").lower()

    if normalized_path in {"", "/", "/index.html"} or normalized_content_type.startswith("text/html"):
        return HTML_CACHE_CONTROL
    if (
        normalized_path.startswith("/api/")
        or normalized_path.startswith("/docs")
        or normalized_path.startswith("/redoc")
        or normalized_path == "/openapi.json"
    ):
        return None
    if normalized_path.startswith("/assets/"):
        return IMMUTABLE_ASSET_CACHE_CONTROL

    suffix = PurePosixPath(normalized_path).suffix
    if normalized_path.startswith("/static/") or suffix in _STATIC_SUFFIXES:
        return STATIC_ASSET_CACHE_CONTROL
    return None


def resolve_static_asset(static_dir: Path, request_path: str) -> Path | None:
    """Resolve a root-level Vite public asset without allowing path traversal."""
    normalized = request_path.lstrip("/")
    if not normalized:
        return None

    relative_path = PurePosixPath(normalized)
    if relative_path.is_absolute() or ".." in relative_path.parts:
        return None

    root = static_dir.resolve()
    candidate = (root / Path(*relative_path.parts)).resolve()
    if not candidate.is_relative_to(root) or not candidate.is_file():
        return None
    return candidate


class StaticAssetCacheMiddleware:
    """Attach explicit cache headers to Vite assets and SPA documents."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        path = str(scope.get("path") or "")

        async def send_with_cache_headers(message: Message) -> None:
            if message["type"] == "http.response.start":
                status = int(message.get("status", 200))
                headers = MutableHeaders(scope=message)
                policy = (
                    cache_control_for_path(path, headers.get("content-type"))
                    if 200 <= status < 300
                    else None
                )
                if policy and "cache-control" not in headers:
                    headers["Cache-Control"] = policy
            await send(message)

        await self.app(scope, receive, send_with_cache_headers)
