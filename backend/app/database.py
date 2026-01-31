#!/usr/bin/env python3
"""
Database module - backward compatibility layer.

This module re-exports from the new modular db package for backward compatibility.
New code should import directly from app.db.
"""

# Re-export everything from the new modular db package
from .db import DatabaseManager, db_manager
from .db.manager import GUID_PATTERN, looks_like_guid

__all__ = ["DatabaseManager", "db_manager", "looks_like_guid", "GUID_PATTERN"]
