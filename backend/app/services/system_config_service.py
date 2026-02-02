from __future__ import annotations

import asyncio
import json
import logging
import sys
from pathlib import Path
from typing import Any

from ..db import db_manager
from .constants import MAX_EMAIL_LIMIT, MIN_EMAIL_LIMIT, SYSTEM_CONFIG_DEFAULTS
from .constants import SYSTEM_CONFIG_FILE as DEFAULT_SYSTEM_CONFIG_FILE

logger = logging.getLogger(__name__)

_system_config_lock = asyncio.Lock()


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
        logger.warning(f"读取系统配置文件失败: {exc}")
        return {}


async def _write_system_config_file(config: dict[str, Any]) -> None:
    config_path = _get_system_config_file()
    async with _system_config_lock:
        try:
            with config_path.open("w", encoding="utf-8") as fp:
                json.dump(config, fp, ensure_ascii=False, indent=2)
        except Exception as exc:
            logger.error(f"写入系统配置文件失败: {exc}", exc_info=True)


def _cast_system_value(key: str, value: Any) -> Any:
    if value is None:
        return value
    if key == "email_limit":
        try:
            limit = int(value)
        except (TypeError, ValueError):
            return SYSTEM_CONFIG_DEFAULTS[key]
        return max(MIN_EMAIL_LIMIT, min(MAX_EMAIL_LIMIT, limit))
    return value


async def load_system_config() -> dict[str, Any]:
    file_config = _read_system_config_file()
    config: dict[str, Any] = {}

    # DB 作为唯一运行时配置源：当 DB 缺失时，用文件/默认值做一次性初始化写入
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

    return config


async def set_system_config_value(key: str, value: Any) -> bool:
    casted = _cast_system_value(key, value)
    return await db_manager.set_system_config(key, str(casted))


async def get_system_config_value(key: str, default: Any | None = None) -> Any:
    config = await load_system_config()
    return config.get(key, default)
