#!/usr/bin/env python3
"""
Database module - SQLite database management for Outlooker.

This module provides a modular database management system split into:
- connection: Database connection and executor management
- accounts: Account CRUD operations
- email_cache: Email caching operations
- admin: Admin user and refresh token management
- system_config: System configuration and metrics
- audit: Login audit and rate limiting
"""

from .manager import DatabaseManager, db_manager

__all__ = ["DatabaseManager", "db_manager"]
