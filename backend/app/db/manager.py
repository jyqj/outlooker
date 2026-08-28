#!/usr/bin/env python3
"""
Database Manager - Main entry point for database operations.

Combines all database operation mixins into a single manager class.
"""

import logging
import re
from contextlib import closing
from pathlib import Path

from ..migrations import apply_migrations
from ..settings import get_settings
from .account_operations import AccountOperationsMixin
from .accounts import AccountsMixin
from .admin import AdminMixin
from .audit import AuditMixin
from .channeling import ChannelingMixin
from .connection import ConnectionMixin
from .email_cache import EmailCacheMixin
from .oauth_tokens import OAuthTokensMixin
from .outlook_accounts import OutlookAccountsMixin
from .outlook_asset_views import OutlookAssetReadMixin
from .protocol_tasks import ProtocolTasksMixin
from .system_config import SystemConfigMixin
from .tags import TagsMixin

settings = get_settings()
PROJECT_ROOT = Path(__file__).resolve().parents[3]

logger = logging.getLogger(__name__)

GUID_PATTERN = re.compile(r"^[0-9a-fA-F]{8}-(?:[0-9a-fA-F]{4}-){3}[0-9a-fA-F]{12}$")


def looks_like_guid(value: str) -> bool:
    """Check if a string looks like a GUID."""
    if not value:
        return False
    return bool(GUID_PATTERN.match(value.strip()))


class DatabaseManager(
    ConnectionMixin,
    AccountsMixin,
    OutlookAccountsMixin,
    OutlookAssetReadMixin,
    OAuthTokensMixin,
    ChannelingMixin,
    ProtocolTasksMixin,
    AccountOperationsMixin,
    EmailCacheMixin,
    AdminMixin,
    SystemConfigMixin,
    AuditMixin,
    TagsMixin,
):
    """
    Database manager combining all operation mixins.

    This class provides a unified interface for all database operations
    while keeping the implementation modular through mixins.
    """

    def __init__(self, db_path: str = settings.database_path):
        """Initialize the database manager."""
        self._init_connection(db_path, PROJECT_ROOT)
        self.init_database()

    def init_database(self) -> None:
        """Initialize database tables, migrations, and workload-oriented indexes."""
        with closing(self._create_connection()) as conn:
            self._initialize_database_pragmas(conn)
            cursor = conn.cursor()

            # Create accounts table
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS accounts (
                    email TEXT PRIMARY KEY,
                    password TEXT DEFAULT '',
                    client_id TEXT DEFAULT '',
                    refresh_token TEXT NOT NULL,
                    is_used INTEGER NOT NULL DEFAULT 0,
                    last_used_at TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                """
            )

            # Create account tags table
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS account_tags (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    email TEXT NOT NULL,
                    tags TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                """
            )

            # Create email cache table
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS email_cache (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    email TEXT NOT NULL,
                    folder TEXT NOT NULL,
                    message_id TEXT NOT NULL,
                    subject TEXT,
                    sender TEXT,
                    received_date TEXT,
                    body_preview TEXT,
                    body_content TEXT,
                    body_type TEXT DEFAULT 'text',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(email, folder, message_id)
                )
                """
            )

            # Email cache metadata table
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS email_cache_meta (
                    email TEXT NOT NULL,
                    folder TEXT NOT NULL,
                    last_checked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (email, folder)
                )
                """
            )

            # Create system config table
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS system_config (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                """
            )

            conn.commit()

            # Run migrations (may update schema)
            apply_migrations(conn)

            # Remove explicit indexes already covered by PRIMARY KEY / UNIQUE indexes.
            # Keeping duplicates increases every write and the on-disk database size.
            cursor.execute("DROP INDEX IF EXISTS idx_accounts_email")
            cursor.execute("DROP INDEX IF EXISTS idx_email_cache_email_folder_message_id")

            # Replace narrow indexes with workload-aligned covering indexes for
            # Outlook asset list/detail projections.
            cursor.execute("DROP INDEX IF EXISTS idx_outlook_accounts_status")
            cursor.execute("DROP INDEX IF EXISTS idx_oauth_tokens_email_status")
            cursor.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_outlook_accounts_updated_email
                ON outlook_accounts(updated_at DESC, email ASC)
                """
            )
            cursor.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_outlook_accounts_status_updated_email
                ON outlook_accounts(status, updated_at DESC, email ASC)
                """
            )
            cursor.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_outlook_accounts_type_updated_email
                ON outlook_accounts(account_type, updated_at DESC, email ASC)
                """
            )
            cursor.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_oauth_tokens_email_status_id
                ON oauth_tokens(email, status, id DESC)
                """
            )
            cursor.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_account_security_snapshot_email_type_id
                ON account_security_methods_snapshot(email, method_type, id)
                """
            )
            cursor.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_account_operation_audit_email_id
                ON account_operation_audit(email, id DESC)
                """
            )

            # Create indexes after migrations so they always target the final schema.
            # account_tags only exists before the relational tags migration.
            cursor.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='account_tags'"
            )
            if cursor.fetchone():
                cursor.execute(
                    "CREATE INDEX IF NOT EXISTS idx_account_tags_email ON account_tags(email)"
                )

            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_email_cache_email_folder ON email_cache(email, folder)"
            )
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_email_cache_message_id ON email_cache(message_id)"
            )
            cursor.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_email_cache_feed
                ON email_cache(
                    email,
                    folder,
                    CASE
                        WHEN message_id GLOB '[0-9]*' THEN CAST(message_id AS INTEGER)
                        ELSE 0
                    END DESC,
                    received_date DESC,
                    id DESC
                )
                """
            )
            cursor.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_email_cache_retention
                ON email_cache(email, folder, created_at DESC, id DESC)
                """
            )
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_email_cache_meta_checked_at ON email_cache_meta(last_checked_at)"
            )

            conn.commit()
            logger.info("数据库初始化完成")


# Global database manager instance
db_manager = DatabaseManager()
