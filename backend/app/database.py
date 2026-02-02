#!/usr/bin/env python3
"""
Database module - backward compatibility layer.

This module re-exports from the new modular db package for backward compatibility.
New code should import directly from app.db.
"""

import warnings

warnings.warn(
    "app.database 模块已废弃，请使用 app.db.manager 代替。"
    "此兼容层将在未来版本中移除。",
    DeprecationWarning,
    stacklevel=2
)

# Re-export everything from the new modular db package
from .db import DatabaseManager, db_manager
from .db.manager import GUID_PATTERN, looks_like_guid

__all__ = ["DatabaseManager", "db_manager", "looks_like_guid", "GUID_PATTERN"]
