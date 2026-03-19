"""Protocol-based Outlook security management client."""

from __future__ import annotations

import asyncio
import re
from typing import Any
from urllib.parse import urljoin

import httpx

from ...db import db_manager
from ...utils.redaction import redact_log_data
from ..channeling.allocation_service import resolve_channel_proxy
from .errors import OutlookProtocolError
from .fingerprint import build_headers, generate_fingerprint
from .protocol_parsers import (
    _extract_continue_form,
    _extract_flow_token,
    _extract_arr_user_proofs,
    _extract_api_canary,
    _extract_canary,
    _extract_email_proofs,
    _extract_hpgid,
    _extract_ppft,
    _extract_url_post,
    _extract_verify_proof_action,
    _is_continue_page,
)
from .protocol_code_provider import ProtocolCodeProvider

LOGIN_ENTRY_URL = "https://login.live.com/"
ACCOUNT_HOME_URL = "https://account.live.com/"
PROOFS_ADDITIONAL_URL = "https://account.live.com/proofs/manage/additional"
ADD_PROOF_URL = "https://account.live.com/proofs/Add?mpsplit=2&apt=2"


class OutlookProtocolClient:
    """HTTP client with per-session browser fingerprinting for Outlook protocol flows."""

    def __init__(
        self,
        *,
        locale_hint: str = "",
        proxy_url: str | None = None,
        timeout: float = 30.0,
        follow_redirects: bool = True,
    ):
        self.locale_hint = locale_hint
        self.proxy_url = proxy_url
        self.timeout = timeout
        self.follow_redirects = follow_redirects

        self.fingerprint = generate_fingerprint(locale_hint=locale_hint)
        self.default_headers = build_headers(self.fingerprint)
        self._client: httpx.AsyncClient | None = None
        self.logged_in_email: str | None = None
        self._last_login_password: str | None = None

    async def __aenter__(self) -> "OutlookProtocolClient":
        await self._ensure_client()
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        await self.close()

    async def _ensure_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(
                timeout=self.timeout,
                follow_redirects=self.follow_redirects,
                headers=self.default_headers,
                proxy=self.proxy_url,
            )
        return self._client

    async def close(self) -> None:
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    async def reset_session(self, locale_hint: str | None = None) -> None:
        """Drop the current client and generate a fresh fingerprint + cookie jar."""
        await self.close()
        self.fingerprint = generate_fingerprint(locale_hint=locale_hint or self.locale_hint)
        self.default_headers = build_headers(self.fingerprint)

    async def request(
        self,
        method: str,
        url: str,
        *,
        headers: dict[str, str] | None = None,
        params: dict[str, Any] | None = None,
        data: dict[str, Any] | None = None,
        json_data: dict[str, Any] | None = None,
        allow_statuses: set[int] | None = None,
    ) -> httpx.Response:
        client = await self._ensure_client()
        merged_headers = {**self.default_headers, **(headers or {})}
        response = await client.request(
            method,
            url,
            headers=merged_headers,
            params=params,
            data=data,
            json=json_data,
        )
        allowed = allow_statuses or {200}
        if response.status_code not in allowed:
            raise OutlookProtocolError(
                f"Unexpected status {response.status_code} for {method} {url}",
                context={
                    "method": method,
                    "url": url,
                    "status_code": response.status_code,
                    "headers": redact_log_data(dict(merged_headers)),
                    "params": redact_log_data(params or {}),
                    "data": redact_log_data(data or {}),
                    "response_preview": response.text[:300],
                },
            )
        return response

    async def get(
        self,
        url: str,
        *,
        headers: dict[str, str] | None = None,
        params: dict[str, Any] | None = None,
        allow_statuses: set[int] | None = None,
    ) -> httpx.Response:
        return await self.request(
            "GET",
            url,
            headers=headers,
            params=params,
            allow_statuses=allow_statuses or {200},
        )

    async def post(
        self,
        url: str,
        *,
        headers: dict[str, str] | None = None,
        params: dict[str, Any] | None = None,
        data: dict[str, Any] | None = None,
        json_data: dict[str, Any] | None = None,
        allow_statuses: set[int] | None = None,
    ) -> httpx.Response:
        return await self.request(
            "POST",
            url,
            headers=headers,
            params=params,
            data=data,
            json_data=json_data,
            allow_statuses=allow_statuses or {200},
        )

    @property
    def cookies(self) -> dict[str, str]:
        if self._client is None:
            return {}
        return dict(self._client.cookies.items())


async def build_protocol_client_for_channel(
    channel_id: int | None,
    *,
    locale_hint: str = "",
    timeout: float = 30.0,
    follow_redirects: bool = True,
) -> OutlookProtocolClient:
    proxy_url = await resolve_channel_proxy(channel_id)
    return OutlookProtocolClient(
        locale_hint=locale_hint,
        proxy_url=proxy_url,
        timeout=timeout,
        follow_redirects=follow_redirects,
    )

    async def _submit_continue_page(self, html: str, base_url: str) -> httpx.Response | None:
        form = _extract_continue_form(html)
        if not form:
            return None
        action = urljoin(base_url, str(form["action"]))
        inputs = form["inputs"]
        return await self.post(action, data=inputs, allow_statuses={200, 302})

    async def _record_protocol_operation(
        self,
        operation: str,
        result: str = "success",
        details: dict[str, Any] | None = None,
    ) -> None:
        email = self.logged_in_email or ""
        if not email:
            return
        await db_manager.insert_account_operation_audit(
            email=email,
            operation=operation,
            operator="protocol",
            result=result,
            details=str(redact_log_data(details or {})),
        )

    async def _handle_post_login_pages(self, response: httpx.Response) -> httpx.Response:
        current = response
        for _ in range(3):
            html = current.text
            lowered = html.lower()

            if "keep me signed in" in lowered or "kmsi" in lowered:
                ppft = _extract_ppft(html)
                url_post = urljoin(str(current.url), _extract_url_post(html))
                current = await self.post(
                    url_post,
                    data={
                        "PPFT": ppft,
                        "LoginOptions": "1",
                        "type": "28",
                    },
                    allow_statuses={200, 302},
                )
                continue

            if _is_continue_page(html):
                next_response = await self._submit_continue_page(html, str(current.url))
                if next_response is None:
                    break
                current = next_response
                continue

            break
        return current

    async def _run_with_retries(
        self,
        operation,
        *,
        max_retries: int = 5,
        backoff_seconds: float = 1.0,
    ):
        last_error: Exception | None = None
        for attempt in range(max_retries):
            try:
                return await operation()
            except Exception as exc:  # noqa: BLE001
                last_error = exc
                if attempt >= max_retries - 1:
                    break
                await self.reset_session()
                if self.logged_in_email and self._last_login_password:
                    await self.login(self.logged_in_email, self._last_login_password)
                await asyncio.sleep(backoff_seconds * (2**attempt))

        if last_error:
            raise OutlookProtocolError("Protocol operation failed after retries", {"error": str(last_error)})
        raise OutlookProtocolError("Protocol operation failed after retries")

    async def login(self, email: str, password: str) -> dict[str, Any]:
        """Phase 1: login.live.com 登录并建立 account.live.com 会话。"""
        initial = await self.get(LOGIN_ENTRY_URL, allow_statuses={200})
        initial_html = initial.text
        ppft = _extract_ppft(initial_html)
        url_post = urljoin(str(initial.url), _extract_url_post(initial_html))

        email_response = await self.post(
            url_post,
            data={
                "login": email,
                "loginfmt": email,
                "type": "11",
                "PPFT": ppft,
                "PPSX": "Passpor",
                "NewUser": "1",
                "FoundMSAs": "",
                "fspost": "0",
                "i21": "0",
                "CookieDisclosure": "0",
                "IsFidoSupported": "1",
                "isSignupPost": "0",
                "i2": "1",
                "i13": "0",
                "i17": "0",
                "i18": "__Login_Host|1",
            },
            allow_statuses={200, 302},
        )
        email_html = email_response.text
        lowered_email = email_html.lower()
        if "usernameerror" in lowered_email or "doesn’t exist" in lowered_email or "doesn't exist" in lowered_email:
            raise OutlookProtocolError("Username/email rejected", {"email": email})

        try:
            ppft = _extract_ppft(email_html)
        except Exception:
            pass
        try:
            url_post = urljoin(str(email_response.url), _extract_url_post(email_html))
        except Exception:
            pass

        password_response = await self.post(
            url_post,
            data={
                "login": email,
                "loginfmt": email,
                "passwd": password,
                "type": "11",
                "PPFT": ppft,
                "PPSX": "Passpor",
                "NewUser": "1",
                "LoginOptions": "3",
                "i21": "0",
                "CookieDisclosure": "0",
                "IsFidoSupported": "1",
            },
            allow_statuses={200, 302},
        )
        password_html = password_response.text
        lowered_password = password_html.lower()
        if "passworderror" in lowered_password or "incorrect password" in lowered_password:
            raise OutlookProtocolError("Password rejected", {"email": email})
        if "account has been locked" in lowered_password or "temporarily blocked" in lowered_password:
            raise OutlookProtocolError("Account locked", {"email": email})

        post_login = await self._handle_post_login_pages(password_response)
        await self.get(ACCOUNT_HOME_URL, allow_statuses={200, 302})
        self.logged_in_email = email
        self._last_login_password = password
        await self._record_protocol_operation("protocol_login", "success", {"email": email})
        return {
            "email": email,
            "final_url": str(post_login.url),
            "cookies": redact_log_data(self.cookies),
            "fingerprint": redact_log_data(self.fingerprint),
        }

    def _select_email_proof(self, proofs: list[dict[str, Any]], recovery_email: str) -> dict[str, Any]:
        recovery_email_lower = recovery_email.lower()
        for proof in proofs:
            display = str(proof.get("display", "")).lower()
            clear_digits = str(proof.get("clearDigits", "")).lower()
            if recovery_email_lower in display or recovery_email_lower.startswith(clear_digits):
                return proof
        for proof in proofs:
            if str(proof.get("type")) == "1" and proof.get("otcEnabled"):
                return proof
        raise OutlookProtocolError("No matching proof found", {"recovery_email": recovery_email})

    async def verify_identity(
        self,
        recovery_email: str,
        code_provider: ProtocolCodeProvider,
        *,
        max_retries: int = 5,
        timeout: int = 150,
        poll_interval: int = 5,
        min_email_id: int | None = None,
    ) -> dict[str, Any]:
        """Phase 2: verify identity via recovery email OTC."""
        if not self.logged_in_email:
            raise OutlookProtocolError("Not logged in")

        async def _operation() -> dict[str, Any]:
                response = await self.get(
                    "https://account.live.com/proofs/manage/additional",
                    allow_statuses={200, 302},
                )
                html = response.text
                proofs = _extract_arr_user_proofs(html)
                if not proofs and self._last_login_password:
                    await self.login(self.logged_in_email, self._last_login_password)
                    response = await self.get(
                        "https://account.live.com/proofs/manage/additional",
                        allow_statuses={200, 302},
                    )
                    html = response.text
                    proofs = _extract_arr_user_proofs(html)

                proof = self._select_email_proof(proofs, recovery_email)
                flow_token = _extract_flow_token(html)

                otc_response = await self.post(
                    "https://login.live.com/GetOneTimeCode.srf",
                    headers={"Accept": "application/json, text/plain, */*"},
                    data={
                        "channel": "Email",
                        "AltEmailE": proof.get("data", ""),
                        "FlowToken": flow_token,
                    },
                    allow_statuses={200},
                )
                otc_payload = otc_response.json()
                if str(otc_payload.get("State")) not in {"200", "201"}:
                    raise OutlookProtocolError("Failed to request OTC", {"response": otc_payload})

                fetched = await code_provider.fetch_code(
                    recovery_email,
                    min_email_id=min_email_id,
                    timeout=timeout,
                    poll_interval=poll_interval,
                )

                submit_url = "https://login.live.com/ppsecure/post.srf"
                try:
                    submit_url = urljoin(str(response.url), _extract_url_post(html))
                except Exception:
                    pass

                code_submit = await self.post(
                    submit_url,
                    data={
                        "otc": fetched.code,
                        "SentProofIDE": proof.get("data", ""),
                        "login": self.logged_in_email,
                        "FlowToken": otc_payload.get("FlowToken") or flow_token,
                        "PPFT": flow_token,
                    },
                    allow_statuses={200, 302},
                )
                final_response = await self._handle_post_login_pages(code_submit)
                return {
                    "verified": True,
                    "email": self.logged_in_email,
                    "proof": redact_log_data(proof),
                    "final_url": str(final_response.url),
                }

        result = await self._run_with_retries(_operation, max_retries=max_retries)
        await self._record_protocol_operation(
            "protocol_verify_identity",
            "success",
            {"recovery_email": recovery_email},
        )
        return result

    async def list_proofs(self) -> dict[str, Any]:
        """List currently available security proofs after login."""
        if not self.logged_in_email:
            raise OutlookProtocolError("Not logged in")
        response = await self.get(PROOFS_ADDITIONAL_URL, allow_statuses={200, 302})
        html = response.text
        proofs = []
        email_proofs = []
        try:
            proofs = _extract_arr_user_proofs(html)
        except Exception:
            pass
        try:
            email_proofs = _extract_email_proofs(html)
        except Exception:
            pass
        result = {
            "email": self.logged_in_email,
            "proofs": redact_log_data(proofs),
            "email_proofs": redact_log_data(email_proofs),
            "url": str(response.url),
        }
        await self._record_protocol_operation("protocol_list_proofs", "success")
        return result

    async def add_recovery_email(
        self,
        new_email: str,
        code_provider: ProtocolCodeProvider,
        *,
        timeout: int = 150,
        poll_interval: int = 5,
        min_email_id: int | None = None,
    ) -> dict[str, Any]:
        """Phase 3: add a new recovery email and verify it via OTC."""
        if not self.logged_in_email:
            raise OutlookProtocolError("Not logged in")

        page = await self.get(ADD_PROOF_URL, allow_statuses={200, 302})
        html = page.text
        canary = _extract_canary(html)
        submit_url = urljoin(str(page.url), "https://account.live.com/proofs/Add")

        add_response = await self.post(
            submit_url,
            data={
                "canary": canary,
                "EmailAddress": new_email,
                "iProofOptions": "Email",
                "action": "AddProof",
            },
            allow_statuses={200, 302},
        )
        add_html = add_response.text
        lowered = add_html.lower()
        if "already part of your security" in lowered:
            raise OutlookProtocolError("Recovery email already bound", {"new_email": new_email})
        if "not a valid email" in lowered:
            raise OutlookProtocolError("Invalid recovery email", {"new_email": new_email})

        verify_action = urljoin(str(add_response.url), _extract_verify_proof_action(add_html))
        fetched = await code_provider.fetch_code(
            new_email,
            min_email_id=min_email_id,
            timeout=timeout,
            poll_interval=poll_interval,
        )
        verify_response = await self.post(
            verify_action,
            data={
                "iOttText": fetched.code,
                "action": "VerifyProof",
                "canary": canary,
            },
            allow_statuses={200, 302},
        )
        final_response = await self._handle_post_login_pages(verify_response)
        result = {
            "added": True,
            "email": self.logged_in_email,
            "recovery_email": new_email,
            "final_url": str(final_response.url),
        }
        await self._record_protocol_operation(
            "protocol_add_recovery_email",
            "success",
            {"recovery_email": new_email},
        )
        return result

    async def remove_recovery_email(self, email_to_remove: str) -> dict[str, Any]:
        """Phase 4: remove an existing recovery email via V2 JSON API."""
        if not self.logged_in_email:
            raise OutlookProtocolError("Not logged in")

        page = await self.get(PROOFS_ADDITIONAL_URL, allow_statuses={200, 302})
        html = page.text
        api_canary = _extract_api_canary(html)
        hpgid = re.sub(r"\s+", "", _extract_hpgid(html))
        email_proofs = _extract_email_proofs(html)

        proof = None
        target_lower = email_to_remove.lower()
        for item in email_proofs:
            display = str(item.get("displayProofId", "")).lower()
            if display == target_lower:
                proof = item
                break
        if proof is None:
            raise OutlookProtocolError("Recovery email proof not found", {"email_to_remove": email_to_remove})

        response = await self.post(
            "https://account.live.com/API/Proofs/DeleteProof",
            headers={
                "Content-Type": "application/json",
                "canary": api_canary,
                "hpgid": hpgid,
            },
            json_data={"proofId": proof.get("proofId", "")},
            allow_statuses={200},
        )
        result = {
            "removed": True,
            "email": self.logged_in_email,
            "recovery_email": email_to_remove,
            "response_preview": response.text[:200],
        }
        await self._record_protocol_operation(
            "protocol_remove_recovery_email",
            "success",
            {"recovery_email": email_to_remove},
        )
        return result

    async def replace_recovery_email(
        self,
        old_email: str,
        new_email: str,
        code_provider: ProtocolCodeProvider,
        *,
        verification_email: str | None = None,
        timeout: int = 150,
        poll_interval: int = 5,
        min_email_id: int | None = None,
    ) -> dict[str, Any]:
        """Phase 5: replace recovery email by verify -> add new -> remove old."""
        await self.verify_identity(
            verification_email or old_email,
            code_provider,
            timeout=timeout,
            poll_interval=poll_interval,
            min_email_id=min_email_id,
        )
        added = await self.add_recovery_email(
            new_email,
            code_provider,
            timeout=timeout,
            poll_interval=poll_interval,
            min_email_id=min_email_id,
        )
        removed = await self.remove_recovery_email(old_email)
        result = {
            "replaced": True,
            "email": self.logged_in_email,
            "old_email": old_email,
            "new_email": new_email,
            "added": added,
            "removed": removed,
        }
        await self._record_protocol_operation(
            "protocol_replace_recovery_email",
            "success",
            {"old_email": old_email, "new_email": new_email},
        )
        return result
