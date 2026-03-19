from __future__ import annotations

import asyncio
import json
import logging
import sys
import time
from pathlib import Path
from typing import Any

from ..db import db_manager
from .constants import (
    BOOL_CONFIG_KEYS,
    INT_CONFIG_KEYS,
    MAX_EMAIL_LIMIT,
    MIN_EMAIL_LIMIT,
    STR_CONFIG_KEYS,
    SYSTEM_CONFIG_DEFAULTS,
)
from .constants import SYSTEM_CONFIG_FILE as DEFAULT_SYSTEM_CONFIG_FILE

logger = logging.getLogger(__name__)

_system_config_lock = asyncio.Lock()

_config_cache: dict[str, Any] | None = None
_config_cache_ts: float = 0.0
_CONFIG_CACHE_TTL = 30.0


def _get_system_config_file() -> Path:
    services_module = sys.modules.get("app.services")
    if services_module is None:
        return DEFAULT_SYSTEM_CONFIG_FILE
    return getattr(services_module, "SYSTEM_CONFIG_FILE", DEFAULT_SYSTEM_CONFIG_FILE)


def _read_system_config_file() -> dict[str, Any]:
    config_path = _get_system_config_file()
    if not config_path.exists():
        return {}

    try:
        with config_path.open("r", encoding="utf-8") as fp:
            return json.load(fp)
    except Exception as exc:
        logger.warning("读取系统配置文件失败: %s", exc)
        return {}


async def _write_system_config_file(config: dict[str, Any]) -> None:
    config_path = _get_system_config_file()
    async with _system_config_lock:
        try:
            with config_path.open("w", encoding="utf-8") as fp:
                json.dump(config, fp, ensure_ascii=False, indent=2)
        except Exception as exc:
            logger.error("写入系统配置文件失败: %s", exc, exc_info=True)


def _cast_system_value(key: str, value: Any) -> Any:
    if value is None:
        return SYSTEM_CONFIG_DEFAULTS.get(key)

    if key in BOOL_CONFIG_KEYS:
        if isinstance(value, str):
            return value.lower() in ("true", "1", "yes")
        return bool(value)

    if key in INT_CONFIG_KEYS:
        try:
            v = int(value)
        except (TypeError, ValueError):
            return SYSTEM_CONFIG_DEFAULTS.get(key)
        if key == "email_limit":
            return max(MIN_EMAIL_LIMIT, min(MAX_EMAIL_LIMIT, v))
        if key == "token_refresh_interval_hours":
            return max(1, min(168, v))
        return v

    if key in STR_CONFIG_KEYS:
        return str(value).strip()

    return value


async def load_system_config() -> dict[str, Any]:
    global _config_cache, _config_cache_ts

    file_config = _read_system_config_file()
    config: dict[str, Any] = {}

    async with _system_config_lock:
        for key, default_value in SYSTEM_CONFIG_DEFAULTS.items():
            db_value = await db_manager.get_system_config(key)
            if db_value is not None:
                config[key] = _cast_system_value(key, db_value)
                continue

            bootstrap_value = file_config.get(key, default_value)
            casted = _cast_system_value(key, bootstrap_value)
            config[key] = casted
            try:
                await db_manager.set_system_config(key, str(casted))
            except Exception as exc:
                logger.warning("写入系统配置到数据库失败(%s): %s", key, exc)

    _config_cache = dict(config)
    _config_cache_ts = time.monotonic()
    return config


def invalidate_config_cache() -> None:
    """Invalidate the in-memory config cache so the next read hits the DB."""
    global _config_cache, _config_cache_ts
    _config_cache = None
    _config_cache_ts = 0.0


async def set_system_config_value(key: str, value: Any) -> bool:
    casted = _cast_system_value(key, value)
    result = await db_manager.set_system_config(key, str(casted))
    if result:
        invalidate_config_cache()
    return result


async def get_system_config_value(key: str, default: Any | None = None) -> Any:
    config = await load_system_config()
    return config.get(key, default)
