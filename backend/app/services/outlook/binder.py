"""Browser fallback binder for Outlook recovery email operations."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, Awaitable, Callable
from urllib.parse import parse_qs, urlencode, urlparse

import httpx

from ...db import db_manager
from ...settings import get_settings
from ..channeling.allocation_service import resolve_channel_proxy
from .graph_token_service import get_default_oauth_config
from .protocol import ADD_PROOF_URL, PROOFS_ADDITIONAL_URL
from .protocol_code_provider import ProtocolCodeProvider

LOGIN_URL = "https://login.live.com/"
SECURITY_URL = "https://account.microsoft.com/security"

EMAIL_INPUT_SELECTORS = (
    'input[type="email"]',
    'input[name="loginfmt"]',
    'input[name="fmt"]',
)
PASSWORD_INPUT_SELECTORS = (
    'input[type="password"]',
    'input[name="passwd"]',
)
SECONDARY_EMAIL_INPUT_SELECTORS = (
    'input[type="email"]',
    'input[name="EmailAddress"]',
    'input[name="iProofOptions"]',
)
CODE_INPUT_SELECTORS = (
    'input[autocomplete="one-time-code"]',
    'input[name="otc"]',
    'input[name="iOttText"]',
    'input[type="tel"]',
    'input[type="number"]',
    'input[inputmode="numeric"]',
)
REMOVE_BUTTON_LABELS = ("Remove", "Delete", "移除", "删除")
NEXT_BUTTON_LABELS = ("Next", "Continue", "Send code", "Verify", "Submit", "下一步", "继续", "验证")
CONSENT_BUTTON_LABELS = ("Accept", "Yes", "Continue", "接受", "同意", "是")

StepCallback = Callable[[str, dict[str, Any]], Awaitable[None] | None]


class BrowserFallbackError(RuntimeError):
    """Raised when the browser fallback flow cannot continue."""


@dataclass
class BrowserFallbackResult:
    email: str
    recovery_email: str
    mode: str
    artifacts: list[str] = field(default_factory=list)
    oauth: dict[str, Any] | None = None
    removed_old_email: bool | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "email": self.email,
            "recovery_email": self.recovery_email,
            "mode": self.mode,
            "artifacts": list(self.artifacts),
            "oauth": self.oauth,
            "removed_old_email": self.removed_old_email,
        }


def _settings():
    return get_settings()


async def _emit(callback: StepCallback | None, step: str, detail: dict[str, Any]) -> None:
    if callback is None:
        return
    result = callback(step, detail)
    if result is not None and hasattr(result, "__await__"):
        await result


def _artifacts_dir(prefix: str) -> Path:
    root = Path(_settings().outlook_browser_fallback_artifacts_dir)
    timestamp = datetime.now(UTC).strftime("%Y%m%d-%H%M%S")
    path = root / f"{prefix}-{timestamp}"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _import_playwright_async():
    try:
        from playwright.async_api import TimeoutError as PlaywrightTimeoutError
        from playwright.async_api import async_playwright
    except Exception as exc:  # noqa: BLE001
        raise BrowserFallbackError(
            "Playwright 不可用，请安装 backend 依赖并执行 `playwright install chromium`"
        ) from exc
    return async_playwright, PlaywrightTimeoutError


async def _screenshot(page: Any, artifacts_dir: Path, step: str, artifacts: list[str]) -> None:
    path = artifacts_dir / f"{step}.png"
    try:
        await page.screenshot(path=str(path), full_page=True)
        artifacts.append(str(path))
    except Exception:
        return


async def _try_click(locator: Any, *, timeout_ms: int = 1500) -> bool:
    try:
        await locator.wait_for(state="visible", timeout=timeout_ms)
        await locator.click(timeout=timeout_ms)
        return True
    except Exception:
        return False


async def _click_labels(page: Any, labels: tuple[str, ...], *, timeout_ms: int = 1500) -> bool:
    for label in labels:
        pattern = re.compile(re.escape(label), re.I)
        for locator in (
            page.get_by_role("button", name=pattern).first,
            page.get_by_role("link", name=pattern).first,
            page.locator(f'text="{label}"').first,
        ):
            if await _try_click(locator, timeout_ms=timeout_ms):
                return True

    try:
        return bool(
            await page.evaluate(
                """
                (labels) => {
                  const candidates = Array.from(document.querySelectorAll('button,a,[role="button"],input[type="button"],input[type="submit"]'));
                  for (const node of candidates) {
                    const text = (node.innerText || node.value || '').trim().toLowerCase();
                    if (labels.some((label) => text.includes(label.toLowerCase()))) {
                      node.click();
                      return true;
                    }
                  }
                  return false;
                }
                """,
                list(labels),
            )
        )
    except Exception:
        return False


async def _fill_first(page: Any, selectors: tuple[str, ...], value: str, *, timeout_ms: int = 2000) -> str:
    for selector in selectors:
        locator = page.locator(selector).first
        try:
            await locator.wait_for(state="visible", timeout=timeout_ms)
            await locator.fill(value, timeout=timeout_ms)
            return selector
        except Exception:
            continue
    raise BrowserFallbackError(f"未找到可输入字段: {selectors}")


async def _wait_for_url_contains(page: Any, fragments: tuple[str, ...], timeout_ms: int) -> None:
    for _ in range(max(1, timeout_ms // 500)):
        current = str(page.url)
        if any(fragment in current for fragment in fragments):
            return
        await page.wait_for_timeout(500)
    raise BrowserFallbackError(f"页面未跳转到预期地址: {fragments}")


async def _assert_not_blocked(page: Any) -> None:
    html = (await page.content()).lower()
    blocked_markers = (
        "captcha",
        "verify you are human",
        "prove you are human",
        "robot",
        "temporarily blocked",
        "unusual activity",
    )
    if any(marker in html for marker in blocked_markers):
        raise BrowserFallbackError("浏览器 fallback 检测到安全挑战，当前任务需要人工介入")


async def _fill_code_and_submit(
    page: Any,
    code_provider: ProtocolCodeProvider,
    target_email: str,
    *,
    min_email_id: int | None = None,
) -> dict[str, Any]:
    fetched = await code_provider.fetch_code(
        target_email,
        min_email_id=min_email_id,
        timeout=_settings().outlook_browser_fallback_timeout_seconds,
        poll_interval=5,
    )
    await _fill_first(page, CODE_INPUT_SELECTORS, fetched.code)
    if not await _click_labels(page, NEXT_BUTTON_LABELS):
        await page.keyboard.press("Enter")
    await page.wait_for_load_state("domcontentloaded")
    await _assert_not_blocked(page)
    return {
        "source": fetched.source,
        "email_id": fetched.email_id,
    }


async def _launch_browser(channel_id: int | None):
    async_playwright, _ = _import_playwright_async()
    proxy_url = await resolve_channel_proxy(channel_id)
    playwright = await async_playwright().start()
    launch_kwargs: dict[str, Any] = {
        "headless": _settings().outlook_browser_fallback_headless,
    }
    if proxy_url:
        launch_kwargs["proxy"] = {"server": proxy_url}
    browser = await playwright.chromium.launch(**launch_kwargs)
    context = await browser.new_context(ignore_https_errors=True)
    await context.add_init_script(
        """
        Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
        window.chrome = window.chrome || { runtime: {} };
        """
    )
    page = await context.new_page()
    timeout_ms = max(30, int(_settings().outlook_browser_fallback_timeout_seconds)) * 1000
    page.set_default_timeout(timeout_ms)
    page.set_default_navigation_timeout(timeout_ms)
    return playwright, browser, context, page


async def _login_with_microsoft(
    page: Any,
    *,
    login_email: str,
    password: str,
    artifacts_dir: Path,
    artifacts: list[str],
) -> None:
    await page.goto(LOGIN_URL, wait_until="domcontentloaded")
    await _screenshot(page, artifacts_dir, "login-entry", artifacts)
    await _fill_first(page, EMAIL_INPUT_SELECTORS, login_email)
    await page.keyboard.press("Enter")
    await page.wait_for_load_state("domcontentloaded")

    await _click_labels(page, ("Use your password", "Password", "使用密码"), timeout_ms=1000)
    await _fill_first(page, PASSWORD_INPUT_SELECTORS, password)
    await page.keyboard.press("Enter")
    await page.wait_for_load_state("domcontentloaded")
    await _click_labels(page, ("No", "Not now", "否", "稍后"), timeout_ms=1000)
    await _assert_not_blocked(page)
    await _screenshot(page, artifacts_dir, "login-success", artifacts)


async def _open_add_secondary_email_form(page: Any) -> None:
    await page.goto(ADD_PROOF_URL, wait_until="domcontentloaded")
    if await page.locator(SECONDARY_EMAIL_INPUT_SELECTORS[0]).count():
        return

    await page.goto(SECURITY_URL, wait_until="domcontentloaded")
    await _click_labels(
        page,
        (
            "Manage how I sign in",
            "Add a new way to sign in or verify",
            "Security info",
            "添加新的登录或验证方式",
            "管理你的登录方式",
        ),
        timeout_ms=3000,
    )
    await page.wait_for_load_state("domcontentloaded")


async def _add_secondary_email_in_browser(
    page: Any,
    *,
    recovery_email: str,
    code_provider: ProtocolCodeProvider,
    min_email_id: int | None,
    artifacts_dir: Path,
    artifacts: list[str],
) -> dict[str, Any]:
    await _open_add_secondary_email_form(page)
    await _screenshot(page, artifacts_dir, "add-secondary-open", artifacts)

    try:
        select = page.locator("select").first
        if await select.count():
            for label in ("An alternate email address", "Alternate email address", "Email"):
                try:
                    await select.select_option(label=label)
                    break
                except Exception:
                    continue
    except Exception:
        pass

    await _fill_first(page, SECONDARY_EMAIL_INPUT_SELECTORS, recovery_email)
    if not await _click_labels(page, NEXT_BUTTON_LABELS):
        await page.keyboard.press("Enter")
    await page.wait_for_load_state("domcontentloaded")
    await _screenshot(page, artifacts_dir, "add-secondary-submitted", artifacts)

    verification = await _fill_code_and_submit(
        page,
        code_provider,
        recovery_email,
        min_email_id=min_email_id,
    )
    await page.wait_for_load_state("domcontentloaded")
    await _screenshot(page, artifacts_dir, "add-secondary-verified", artifacts)
    return {"verification": verification}


async def _remove_secondary_email_in_browser(
    page: Any,
    *,
    old_email: str,
    artifacts_dir: Path,
    artifacts: list[str],
) -> bool:
    await page.goto(PROOFS_ADDITIONAL_URL, wait_until="domcontentloaded")
    await _screenshot(page, artifacts_dir, "remove-secondary-open", artifacts)

    clicked = bool(
        await page.evaluate(
            """
            ({ oldEmail, labels }) => {
              const candidates = Array.from(document.querySelectorAll('tr,li,div,section'));
              for (const node of candidates) {
                const text = (node.innerText || '').toLowerCase();
                if (!text.includes(oldEmail.toLowerCase())) {
                  continue;
                }
                const button = Array.from(node.querySelectorAll('button,a,[role="button"],input[type="button"],input[type="submit"]'))
                  .find((child) => labels.some((label) => ((child.innerText || child.value || '').toLowerCase().includes(label.toLowerCase()))));
                if (button) {
                  button.click();
                  return true;
                }
              }
              return false;
            }
            """,
            {"oldEmail": old_email, "labels": list(REMOVE_BUTTON_LABELS)},
        )
    )
    if not clicked:
        if not await _click_labels(page, REMOVE_BUTTON_LABELS, timeout_ms=1500):
            return False

    await _click_labels(page, ("Remove", "Delete", "Yes", "Confirm", "删除", "确认", "是"), timeout_ms=3000)
    await page.wait_for_load_state("domcontentloaded")
    await _screenshot(page, artifacts_dir, "remove-secondary-done", artifacts)
    return True


async def _exchange_auth_code(
    code: str,
    *,
    email: str,
    channel_id: int | None,
) -> dict[str, Any]:
    config = await get_default_oauth_config()
    post_data: dict[str, str] = {
        "client_id": config.get("client_id", ""),
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": config.get("redirect_uri", ""),
        "scope": config.get("scopes", ""),
    }
    if config.get("client_secret"):
        post_data["client_secret"] = str(config["client_secret"])

    proxy_url = await resolve_channel_proxy(channel_id)
    async with httpx.AsyncClient(timeout=15.0, proxy=proxy_url) as client:
        response = await client.post(str(config["token_url"]), data=post_data)
    if response.status_code != 200:
        raise BrowserFallbackError(f"浏览器 OAuth 交换失败: {response.text[:200]}")

    payload = response.json()
    expires_in = int(payload.get("expires_in", 3600))
    expires_at = (datetime.now(UTC) + timedelta(seconds=expires_in)).isoformat()

    if not await db_manager.get_outlook_account(email):
        await db_manager.create_outlook_account(
            email=email,
            status="active",
            account_type="consumer",
            source_account_email=email,
            notes="created via browser fallback oauth capture",
        )

    existing = await db_manager.get_latest_active_oauth_token(email)
    if existing:
        await db_manager.update_oauth_token(
            int(existing["id"]),
            access_token=payload.get("access_token", ""),
            refresh_token=payload.get("refresh_token", ""),
            expires_at=expires_at,
            scopes_granted=payload.get("scope", config.get("scopes", "")),
            status="active",
            last_error="",
        )
        token_id = int(existing["id"])
    else:
        token_id = await db_manager.create_oauth_token(
            oauth_config_id=int(config["id"]),
            email=email,
            access_token=payload.get("access_token", ""),
            refresh_token=payload.get("refresh_token", ""),
            expires_at=expires_at,
            scopes_granted=payload.get("scope", config.get("scopes", "")),
            status="active",
            last_error="",
        )

    refresh_token = str(payload.get("refresh_token") or "")
    if refresh_token and await db_manager.get_account(email):
        await db_manager.update_account(email, refresh_token=refresh_token)

    from .graph import sync_account_capabilities

    await sync_account_capabilities(email)
    token = await db_manager.get_oauth_token_by_id(token_id)
    return {
        "token_id": token_id,
        "expires_at": expires_at,
        "scopes": token.get("scopes_granted") if token else payload.get("scope", ""),
    }


async def obtain_oauth_tokens_via_browser(
    page: Any,
    *,
    email: str,
    channel_id: int | None,
    artifacts_dir: Path,
    artifacts: list[str],
) -> dict[str, Any]:
    config = await get_default_oauth_config()
    query = urlencode(
        {
            "client_id": config.get("client_id", ""),
            "response_type": "code",
            "redirect_uri": config.get("redirect_uri", ""),
            "response_mode": "query",
            "scope": config.get("scopes", ""),
            "prompt": "consent",
            "state": "browser-fallback",
        }
    )
    auth_url = f"{config.get('authorization_url')}?{query}"
    await page.goto(auth_url, wait_until="domcontentloaded")
    await _click_labels(page, CONSENT_BUTTON_LABELS, timeout_ms=3000)
    await _wait_for_url_contains(page, ("code=",), timeout_ms=_settings().outlook_browser_fallback_timeout_seconds * 1000)
    await _screenshot(page, artifacts_dir, "oauth-consent", artifacts)
    parsed = urlparse(str(page.url))
    code = parse_qs(parsed.query).get("code", [""])[0]
    if not code:
        raise BrowserFallbackError("浏览器 OAuth 未返回 authorization code")
    return await _exchange_auth_code(code, email=email, channel_id=channel_id)


async def bind_secondary_email_with_browser(
    *,
    login_email: str,
    password: str,
    recovery_email: str,
    code_provider: ProtocolCodeProvider,
    verification_email: str | None = None,
    channel_id: int | None = None,
    min_email_id: int | None = None,
    capture_oauth: bool | None = None,
    step_callback: StepCallback | None = None,
) -> dict[str, Any]:
    artifacts_dir = _artifacts_dir("browser-bind")
    artifacts: list[str] = []
    playwright = browser = context = page = None
    await _emit(step_callback, "browser_fallback:start", {"mode": "bind", "recovery_email": recovery_email})
    try:
        playwright, browser, context, page = await _launch_browser(channel_id)
        await _login_with_microsoft(
            page,
            login_email=login_email,
            password=password,
            artifacts_dir=artifacts_dir,
            artifacts=artifacts,
        )
        if verification_email:
            await _emit(step_callback, "browser_fallback:verification_prompt", {"verification_email": verification_email})
        add_result = await _add_secondary_email_in_browser(
            page,
            recovery_email=recovery_email,
            code_provider=code_provider,
            min_email_id=min_email_id,
            artifacts_dir=artifacts_dir,
            artifacts=artifacts,
        )
        oauth_result = None
        should_capture = _settings().outlook_browser_fallback_capture_oauth if capture_oauth is None else capture_oauth
        if should_capture:
            oauth_result = await obtain_oauth_tokens_via_browser(
                page,
                email=login_email,
                channel_id=channel_id,
                artifacts_dir=artifacts_dir,
                artifacts=artifacts,
            )

        result = BrowserFallbackResult(
            email=login_email,
            recovery_email=recovery_email,
            mode="bind",
            artifacts=artifacts,
            oauth=oauth_result,
        )
        payload = {**result.to_dict(), **add_result}
        await _emit(step_callback, "browser_fallback:success", payload)
        return payload
    finally:
        for closable in (page, context, browser):
            if closable is None:
                continue
            try:
                await closable.close()
            except Exception:
                pass
        if playwright is not None:
            try:
                await playwright.stop()
            except Exception:
                pass


async def replace_secondary_email_with_browser(
    *,
    login_email: str,
    password: str,
    old_email: str,
    new_email: str,
    code_provider: ProtocolCodeProvider,
    verification_email: str | None = None,
    channel_id: int | None = None,
    min_email_id: int | None = None,
    capture_oauth: bool | None = None,
    step_callback: StepCallback | None = None,
) -> dict[str, Any]:
    artifacts_dir = _artifacts_dir("browser-rebind")
    artifacts: list[str] = []
    playwright = browser = context = page = None
    await _emit(
        step_callback,
        "browser_fallback:start",
        {"mode": "rebind", "old_email": old_email, "new_email": new_email},
    )
    try:
        playwright, browser, context, page = await _launch_browser(channel_id)
        await _login_with_microsoft(
            page,
            login_email=login_email,
            password=password,
            artifacts_dir=artifacts_dir,
            artifacts=artifacts,
        )
        if verification_email:
            await _emit(step_callback, "browser_fallback:verification_prompt", {"verification_email": verification_email})

        add_result = await _add_secondary_email_in_browser(
            page,
            recovery_email=new_email,
            code_provider=code_provider,
            min_email_id=min_email_id,
            artifacts_dir=artifacts_dir,
            artifacts=artifacts,
        )
        removed = await _remove_secondary_email_in_browser(
            page,
            old_email=old_email,
            artifacts_dir=artifacts_dir,
            artifacts=artifacts,
        )
        if not removed:
            raise BrowserFallbackError(f"浏览器 fallback 未能移除旧恢复邮箱: {old_email}")
        oauth_result = None
        should_capture = _settings().outlook_browser_fallback_capture_oauth if capture_oauth is None else capture_oauth
        if should_capture:
            oauth_result = await obtain_oauth_tokens_via_browser(
                page,
                email=login_email,
                channel_id=channel_id,
                artifacts_dir=artifacts_dir,
                artifacts=artifacts,
            )

        result = BrowserFallbackResult(
            email=login_email,
            recovery_email=new_email,
            mode="rebind",
            artifacts=artifacts,
            oauth=oauth_result,
            removed_old_email=removed,
        )
        payload = {**result.to_dict(), **add_result, "old_email": old_email}
        await _emit(step_callback, "browser_fallback:success", payload)
        return payload
    finally:
        for closable in (page, context, browser):
            if closable is None:
                continue
            try:
                await closable.close()
            except Exception:
                pass
        if playwright is not None:
            try:
                await playwright.stop()
            except Exception:
                pass
