"""Browser fingerprint randomization for protocol-based Outlook operations."""

from __future__ import annotations

import random
import uuid
from typing import Any

_CHROME_VERSIONS = [
    (120, 0, 6099, 225), (121, 0, 6167, 160), (122, 0, 6261, 112),
    (123, 0, 6312, 86), (124, 0, 6367, 201), (125, 0, 6422, 141),
    (126, 0, 6478, 126), (127, 0, 6533, 99), (128, 0, 6613, 137),
    (129, 0, 6668, 89), (130, 0, 6723, 116), (131, 0, 6778, 139),
    (132, 0, 6834, 110), (133, 0, 6943, 98), (134, 0, 6998, 62),
]

_EDGE_VERSIONS = [
    (120, 0, 2210, 144), (121, 0, 2277, 128), (122, 0, 2365, 92),
    (123, 0, 2420, 97), (124, 0, 2478, 105), (125, 0, 2535, 92),
    (126, 0, 2592, 113), (127, 0, 2651, 105), (128, 0, 2739, 79),
    (129, 0, 2792, 89), (130, 0, 2849, 80), (131, 0, 2903, 112),
]

_WIN_BUILDS = ["10.0", "10.0", "10.0", "11.0"]
_WIN_BUILD_NUMBERS = [19041, 19042, 19043, 19044, 19045, 22621, 22631, 26100]

_MAC_VERSIONS = [
    "10_15_7", "11_6_8", "12_7_4", "13_6_4", "14_3_1", "14_4_1", "14_5",
    "15_0", "15_1", "15_2",
]

_LOCALES = [
    ("en-US", "en-US,en;q=0.9"),
    ("en-GB", "en-GB,en;q=0.9"),
    ("ja-JP", "ja-JP,ja;q=0.9,en;q=0.8"),
    ("zh-CN", "zh-CN,zh;q=0.9,en;q=0.8"),
    ("de-DE", "de-DE,de;q=0.9,en;q=0.8"),
    ("fr-FR", "fr-FR,fr;q=0.9,en;q=0.8"),
    ("ko-KR", "ko-KR,ko;q=0.9,en;q=0.8"),
    ("pt-BR", "pt-BR,pt;q=0.9,en;q=0.8"),
    ("es-ES", "es-ES,es;q=0.9,en;q=0.8"),
]

_SCREENS = [
    (1920, 1080), (2560, 1440), (1366, 768), (1440, 900),
    (1536, 864), (1680, 1050), (3840, 2160), (2560, 1080),
]

_TIMEZONES_BY_LOCALE = {
    "en-US": ["America/New_York", "America/Chicago", "America/Denver", "America/Los_Angeles"],
    "en-GB": ["Europe/London"],
    "ja-JP": ["Asia/Tokyo"],
    "zh-CN": ["Asia/Shanghai", "Asia/Hong_Kong"],
    "de-DE": ["Europe/Berlin"],
    "fr-FR": ["Europe/Paris"],
    "ko-KR": ["Asia/Seoul"],
    "pt-BR": ["America/Sao_Paulo"],
    "es-ES": ["Europe/Madrid"],
}


def generate_fingerprint(locale_hint: str = "") -> dict[str, Any]:
    os_type = random.choice(["windows", "windows", "windows", "mac"])

    if os_type == "windows":
        win_ver = random.choice(_WIN_BUILDS)
        build = random.choice(_WIN_BUILD_NUMBERS)
        platform_ua = f"(Windows NT {win_ver}; Win64; x64)"
        sec_platform = '"Windows"'
    else:
        mac_ver = random.choice(_MAC_VERSIONS)
        build = mac_ver
        platform_ua = f"(Macintosh; Intel Mac OS X {mac_ver})"
        sec_platform = '"macOS"'

    browser_type = random.choice(["chrome", "chrome", "chrome", "edge"])
    version = random.choice(_CHROME_VERSIONS if browser_type == "chrome" else _EDGE_VERSIONS)
    brand = "Google Chrome" if browser_type == "chrome" else "Microsoft Edge"

    major, minor, build_v, patch = version
    full_ver = f"{major}.{minor}.{build_v}.{patch}"
    user_agent = (
        f"Mozilla/5.0 {platform_ua} AppleWebKit/537.36 "
        f"(KHTML, like Gecko) Chrome/{full_ver} Safari/537.36"
    )
    if browser_type == "edge":
        user_agent += f" Edg/{full_ver}"

    sec_ch_ua = (
        f'"Not A(Brand";v="99", "{brand}";v="{major}", '
        f'"Chromium";v="{major}"'
    )

    if locale_hint and any(lc == locale_hint for lc, _ in _LOCALES):
        locale_code, accept_language = next((lc, al) for lc, al in _LOCALES if lc == locale_hint)
    else:
        locale_code, accept_language = random.choice(_LOCALES)

    screen_width, screen_height = random.choice(_SCREENS)
    timezone = random.choice(_TIMEZONES_BY_LOCALE.get(locale_code, ["UTC"]))

    return {
        "user_agent": user_agent,
        "accept_language": accept_language,
        "sec_ch_ua": sec_ch_ua,
        "sec_ch_ua_platform": sec_platform,
        "sec_ch_ua_mobile": "?0",
        "screen_width": screen_width,
        "screen_height": screen_height,
        "timezone": timezone,
        "locale": locale_code,
        "os_type": os_type,
        "os_build": build,
        "mc1_guid": uuid.uuid4().hex,
        "msfpc_guid": uuid.uuid4().hex,
    }


def build_headers(fingerprint: dict[str, Any]) -> dict[str, str]:
    return {
        "User-Agent": str(fingerprint["user_agent"]),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": str(fingerprint["accept_language"]),
        "Accept-Encoding": "gzip, deflate, br",
        "Cache-Control": "no-cache",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "same-origin",
        "Sec-Fetch-User": "?1",
        "Sec-CH-UA": str(fingerprint["sec_ch_ua"]),
        "Sec-CH-UA-Mobile": str(fingerprint["sec_ch_ua_mobile"]),
        "Sec-CH-UA-Platform": str(fingerprint["sec_ch_ua_platform"]),
        "Upgrade-Insecure-Requests": "1",
    }
