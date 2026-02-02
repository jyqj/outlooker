#!/usr/bin/env python3
"""
通用工具函数包 (分页、规范化等)

注意: 仅放置无副作用的纯函数, 避免引入数据库/网络等重依赖。
"""

from .json_utils import safe_json_dumps, safe_json_loads

__all__ = [
    "safe_json_loads",
    "safe_json_dumps",
]

