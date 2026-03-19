"""HTML and JavaScript parsers for Outlook protocol flows."""

from __future__ import annotations

import json
import re
from typing import Any


SERVER_DATA_RE = re.compile(r"var\s+ServerData\s*=\s*(\{.*?\})\s*;", re.DOTALL)
URL_POST_RE = re.compile(r'"urlPost"\s*:\s*"([^"]+)"')
PPFT_INPUT_RE = re.compile(r'name=["\']PPFT["\']\s+value=["\']([^"\']+)["\']', re.IGNORECASE)
SFT_TAG_RE = re.compile(r'"sFTTag"\s*:\s*"([^"]+)"')
CANARY_INPUT_RE = re.compile(r'name=["\']canary["\']\s+value=["\']([^"\']+)["\']', re.IGNORECASE)
CANARY_JS_RE = re.compile(r'"canary"\s*:\s*"([^"]+)"')
CONFIG_BLOCK_RE = re.compile(r"\$Config\s*=\s*(\{.*?\})\s*;", re.DOTALL)
CONTINUE_FORM_RE = re.compile(r"<form[^>]+action=[\"']([^\"']+)[\"'][^>]*>(.*?)</form>", re.DOTALL | re.IGNORECASE)
INPUT_RE = re.compile(r'<input[^>]+name=["\']([^"\']+)["\'][^>]*value=["\']([^"\']*)["\']', re.IGNORECASE)
FLOW_TOKEN_RE = re.compile(r'"FlowToken"\s*:\s*"([^"]+)"')
VERIFY_ACTION_RE = re.compile(r'<form[^>]+id=["\']frmVerifyProof["\'][^>]+action=["\']([^"\']+)["\']', re.IGNORECASE)


def _extract_server_data_raw(html: str) -> str:
    match = SERVER_DATA_RE.search(html)
    if not match:
        raise ValueError("Failed to extract ServerData")
    return match.group(1)


def _extract_ppft(html: str) -> str:
    for pattern in (PPFT_INPUT_RE, SFT_TAG_RE):
        match = pattern.search(html)
        if match:
            return match.group(1)
    raise ValueError("Failed to extract PPFT/sFT")


def _extract_url_post(html: str) -> str:
    match = URL_POST_RE.search(html)
    if not match:
        raise ValueError("Failed to extract urlPost")
    return match.group(1).replace("\\/", "/")


def _extract_canary(html: str) -> str:
    for pattern in (CANARY_INPUT_RE, CANARY_JS_RE):
        match = pattern.search(html)
        if match:
            return match.group(1).encode("utf-8").decode("unicode_escape")
    raise ValueError("Failed to extract canary")


def _extract_api_canary(html: str) -> str:
    match = CONFIG_BLOCK_RE.search(html)
    if not match:
        raise ValueError("Failed to extract $Config block")
    config_text = match.group(1).encode("utf-8").decode("unicode_escape")
    api_match = re.search(r'"apiCanary"\s*:\s*"([^"]+)"', config_text)
    if not api_match:
        raise ValueError("Failed to extract apiCanary")
    return api_match.group(1)


def _extract_hpgid(html: str) -> str:
    match = CONFIG_BLOCK_RE.search(html)
    if not match:
        raise ValueError("Failed to extract $Config block")
    config_text = match.group(1).encode("utf-8").decode("unicode_escape")
    hpgid_match = re.search(r'"hpgid"\s*:\s*([0-9]+)', config_text)
    if not hpgid_match:
        raise ValueError("Failed to extract hpgid")
    return hpgid_match.group(1)


def _extract_flow_token(html: str) -> str:
    match = FLOW_TOKEN_RE.search(html)
    if match:
        return match.group(1)
    try:
        return _extract_ppft(html)
    except Exception as exc:  # noqa: BLE001
        raise ValueError("Failed to extract FlowToken") from exc


def _find_balanced_json_array(source: str, key: str) -> str:
    key_pos = source.find(key)
    if key_pos == -1:
        raise ValueError(f"Failed to locate array key: {key}")
    start = source.find("[", key_pos)
    if start == -1:
        raise ValueError(f"Failed to locate array start for key: {key}")

    depth = 0
    for idx in range(start, len(source)):
        char = source[idx]
        if char == "[":
            depth += 1
        elif char == "]":
            depth -= 1
            if depth == 0:
                return source[start:idx + 1]
    raise ValueError(f"Unbalanced array for key: {key}")


def _js_object_to_json(text: str) -> str:
    converted = text
    converted = re.sub(r"([{,]\s*)([A-Za-z0-9_]+)\s*:", r'\1"\2":', converted)
    converted = converted.replace("!0", "true").replace("!1", "false")
    converted = converted.replace("\\/", "/")
    converted = re.sub(r",(\s*[}\]])", r"\1", converted)
    return converted


def _extract_server_data_array(html: str, key: str) -> list[dict[str, Any]]:
    raw = _extract_server_data_raw(html)
    array_text = _find_balanced_json_array(raw, key)
    normalized = _js_object_to_json(array_text)
    try:
        return json.loads(normalized)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Failed to decode array {key}") from exc


def _extract_arr_user_proofs(html: str) -> list[dict[str, Any]]:
    return _extract_server_data_array(html, "arrUserProofs")


def _extract_email_proofs(html: str) -> list[dict[str, Any]]:
    config_match = CONFIG_BLOCK_RE.search(html)
    if not config_match:
        raise ValueError("Failed to extract $Config block")
    config_text = config_match.group(1).encode("utf-8").decode("unicode_escape")
    array_text = _find_balanced_json_array(config_text, "emailProofs")
    normalized = _js_object_to_json(array_text)
    try:
        return json.loads(normalized)
    except json.JSONDecodeError as exc:
        raise ValueError("Failed to decode emailProofs") from exc


def _extract_form_inputs(html_fragment: str) -> dict[str, str]:
    return {name: value for name, value in INPUT_RE.findall(html_fragment)}


def _extract_continue_form(html: str) -> dict[str, Any] | None:
    match = CONTINUE_FORM_RE.search(html)
    if not match:
        return None
    action = match.group(1)
    inputs = _extract_form_inputs(match.group(2))
    return {"action": action, "inputs": inputs}


def _is_continue_page(html: str) -> bool:
    lowered = html.lower()
    return "continue" in lowered or "继续" in lowered or "keep me signed in" in lowered


def _extract_verify_proof_action(html: str) -> str:
    match = VERIFY_ACTION_RE.search(html)
    if not match:
        raise ValueError("Failed to extract verify proof action")
    return match.group(1)
