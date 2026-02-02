#!/usr/bin/env python3
"""
JSON utility functions for safe parsing and serialization.
"""

import json
import logging
from typing import overload


@overload
def safe_json_loads(
    value: str | None,
    default: list,
    logger: logging.Logger | None = None,
    context: str = ""
) -> list: ...


@overload
def safe_json_loads(
    value: str | None,
    default: dict,
    logger: logging.Logger | None = None,
    context: str = ""
) -> dict: ...


def safe_json_loads(
    value: str | None,
    default: list | dict,
    logger: logging.Logger | None = None,
    context: str = ""
) -> list | dict:
    """
    安全解析 JSON 字符串，失败时返回默认值并记录日志。
    
    Args:
        value: 要解析的 JSON 字符串
        default: 解析失败时返回的默认值（必须提供）
        logger: 日志记录器
        context: 上下文信息，用于日志
        
    Returns:
        解析后的对象或默认值
    """
    if not value:
        return default
        
    try:
        result = json.loads(value)
        # 类型检查：确保返回类型与 default 一致
        if isinstance(default, list) and not isinstance(result, list):
            if logger:
                logger.warning(f"JSON 解析结果类型不匹配，期望 list{f' ({context})' if context else ''}")
            return default
        if isinstance(default, dict) and not isinstance(result, dict):
            if logger:
                logger.warning(f"JSON 解析结果类型不匹配，期望 dict{f' ({context})' if context else ''}")
            return default
        return result
    except json.JSONDecodeError as e:
        if logger:
            ctx = f" ({context})" if context else ""
            logger.warning(f"JSON 解析失败{ctx}: {e}")
        return default


def safe_json_dumps(
    obj: Any,
    default: str = "[]",
    ensure_ascii: bool = False,
    logger: logging.Logger | None = None,
    context: str = ""
) -> str:
    """
    安全序列化对象为 JSON 字符串。
    
    Args:
        obj: 要序列化的对象
        default: 序列化失败时返回的默认值
        ensure_ascii: 是否转义非 ASCII 字符
        logger: 日志记录器
        context: 上下文信息
        
    Returns:
        JSON 字符串
    """
    try:
        return json.dumps(obj, ensure_ascii=ensure_ascii)
    except (TypeError, ValueError) as e:
        if logger:
            ctx = f" ({context})" if context else ""
            logger.warning(f"JSON 序列化失败{ctx}: {e}")
        return default
