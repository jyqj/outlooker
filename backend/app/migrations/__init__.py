#!/usr/bin/env python3
"""
轻量级数据库迁移框架

通过在应用启动阶段执行 register_migration 注册的迁移函数，保证数据库 schema 可演进。
"""

from __future__ import annotations

import logging
import sqlite3
from dataclasses import dataclass
from typing import Callable, List, Set

from ..settings import get_settings

logger = logging.getLogger(__name__)
_settings = get_settings()
DEFAULT_EMAIL_LIMIT = _settings.default_email_limit
INBOX_FOLDER_NAME = _settings.inbox_folder_name


@dataclass(frozen=True)
class Migration:
    version: str
    description: str
    handler: Callable[[sqlite3.Connection], None]


_REGISTRY: List[Migration] = []


def register_migration(version: str, description: str):
    """注册迁移函数的装饰器"""

    def decorator(func: Callable[[sqlite3.Connection], None]):
        _REGISTRY.append(Migration(version=version, description=description, handler=func))
        return func

    return decorator


def _normalize_registry(registry: List[Migration]) -> List[Migration]:
    """按照版本排序并去重"""
    seen: Set[str] = set()
    ordered: List[Migration] = []
    for migration in sorted(registry, key=lambda m: m.version):
        if migration.version in seen:
            logger.warning("检测到重复的迁移版本号 %s，后者将被忽略", migration.version)
            continue
        seen.add(migration.version)
        ordered.append(migration)
    return ordered


def apply_migrations(conn: sqlite3.Connection) -> None:
    """执行尚未应用的迁移"""
    cursor = conn.cursor()
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS schema_migrations (
            version TEXT PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    conn.commit()

    cursor.execute("SELECT version FROM schema_migrations")
    rows = cursor.fetchall()
    applied = {row[0] if not isinstance(row, sqlite3.Row) else row["version"] for row in rows}

    for migration in _normalize_registry(_REGISTRY):
        if migration.version in applied:
            continue
        logger.info("应用数据库迁移 %s: %s", migration.version, migration.description)
        migration.handler(conn)
        cursor.execute(
            "INSERT INTO schema_migrations (version) VALUES (?)",
            (migration.version,),
        )
        conn.commit()

    logger.info("数据库迁移检查完成，共 %s 个迁移", len(_REGISTRY))


# ============================================================================
# 迁移定义
# ============================================================================


@register_migration("2025012001", "创建 system_metrics 表")
def _create_system_metrics_table(conn: sqlite3.Connection) -> None:
    cursor = conn.cursor()
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS system_metrics (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_system_metrics_updated_at ON system_metrics(updated_at)"
    )


@register_migration("2025012002", "为 email_limit 写入默认配置")
def _backfill_email_limit(conn: sqlite3.Connection) -> None:
    cursor = conn.cursor()
    cursor.execute("SELECT value FROM system_config WHERE key = 'email_limit'")
    row = cursor.fetchone()
    if row is None:
        cursor.execute(
            """
            INSERT INTO system_config (key, value, updated_at)
            VALUES ('email_limit', ?, CURRENT_TIMESTAMP)
            """,
            (str(DEFAULT_EMAIL_LIMIT),),
        )


@register_migration("2025012101", "为 accounts 表增加使用状态字段")
def _add_account_usage_columns(conn: sqlite3.Connection) -> None:
    """为 accounts 表增加 is_used / last_used_at 字段及索引

    - 兼容老库：仅在字段不存在时执行 ALTER TABLE
    - 在测试迁移环境中（无 accounts 表）直接跳过
    """
    cursor = conn.cursor()

    # 若 accounts 表不存在（例如测试迁移用的临时库），直接返回
    cursor.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='accounts'"
    )
    row = cursor.fetchone()
    if not row:
        return

    # 查询已有字段
    cursor.execute("PRAGMA table_info(accounts)")
    columns = {col[1] for col in cursor.fetchall()}

    if "is_used" not in columns:
        cursor.execute(
            "ALTER TABLE accounts ADD COLUMN is_used INTEGER NOT NULL DEFAULT 0"
        )

    if "last_used_at" not in columns:
        cursor.execute(
            "ALTER TABLE accounts ADD COLUMN last_used_at TIMESTAMP"
        )

    # 为查询未使用账户添加复合索引
    cursor.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_accounts_is_used_created_at
        ON accounts(is_used, created_at)
        """
    )


@register_migration("2025012501", "创建管理员与刷新令牌表")
def _create_admin_tables(conn: sqlite3.Connection) -> None:
    cursor = conn.cursor()
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS admin_users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL DEFAULT 'admin',
            is_active INTEGER NOT NULL DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS admin_refresh_tokens (
            token_id TEXT PRIMARY KEY,
            admin_id INTEGER NOT NULL,
            token_hash TEXT NOT NULL,
            user_agent TEXT,
            ip_address TEXT,
            expires_at TIMESTAMP NOT NULL,
            revoked_at TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (admin_id) REFERENCES admin_users(id) ON DELETE CASCADE
        )
        """
    )
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_admin_refresh_admin_id ON admin_refresh_tokens(admin_id)"
    )
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_admin_refresh_expires_at ON admin_refresh_tokens(expires_at)"
    )


@register_migration("2025012502", "创建登录审计与锁定表")
def _create_login_audit_tables(conn: sqlite3.Connection) -> None:
    cursor = conn.cursor()
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS admin_login_attempts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ip TEXT NOT NULL,
            username TEXT NOT NULL,
            success INTEGER NOT NULL,
            reason TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    cursor.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_admin_login_attempts_ip_user_time
        ON admin_login_attempts(ip, username, created_at)
        """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS admin_lockouts (
            ip TEXT NOT NULL,
            username TEXT NOT NULL,
            lockout_until TIMESTAMP NOT NULL,
            PRIMARY KEY (ip, username)
        )
        """
    )
    cursor.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_admin_lockouts_until
        ON admin_lockouts(lockout_until)
        """
    )


@register_migration("2026010901", "升级 email_cache 表结构以支持 folder 维度")
def _upgrade_email_cache_folder(conn: sqlite3.Connection) -> None:
    cursor = conn.cursor()
    cursor.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='email_cache'"
    )
    row = cursor.fetchone()
    if not row:
        return

    cursor.execute("PRAGMA table_info(email_cache)")
    columns = {col[1] for col in cursor.fetchall()}
    has_folder = "folder" in columns

    def _extract_column_name(value):
        if isinstance(value, sqlite3.Row):
            return value["name"]
        return value[2]

    def _has_target_unique_index() -> bool:
        cursor.execute("PRAGMA index_list(email_cache)")
        index_rows = cursor.fetchall()
        for idx in index_rows:
            name = idx["name"] if isinstance(idx, sqlite3.Row) else idx[1]
            unique = idx["unique"] if isinstance(idx, sqlite3.Row) else idx[2]
            if not unique:
                continue
            cursor.execute(f"PRAGMA index_info('{name}')")
            cols = [_extract_column_name(col) for col in cursor.fetchall()]
            if cols == ["email", "folder", "message_id"]:
                return True
        return False

    if has_folder and _has_target_unique_index():
        return

    default_folder = (INBOX_FOLDER_NAME or "INBOX").strip() or "INBOX"
    escaped_folder = default_folder.replace("'", "''")

    cursor.execute(
        f"""
        CREATE TABLE IF NOT EXISTS email_cache_new (
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

    if has_folder:
        cursor.execute(
            f"""
            INSERT OR REPLACE INTO email_cache_new
            (email, folder, message_id, subject, sender, received_date, body_preview, body_content, body_type, created_at)
            SELECT
              email,
              COALESCE(NULLIF(TRIM(folder), ''), '{escaped_folder}'),
              message_id,
              subject,
              sender,
              received_date,
              body_preview,
              body_content,
              body_type,
              created_at
            FROM email_cache
            """
        )
    else:
        cursor.execute(
            f"""
            INSERT OR REPLACE INTO email_cache_new
            (email, folder, message_id, subject, sender, received_date, body_preview, body_content, body_type, created_at)
            SELECT
              email,
              '{escaped_folder}',
              message_id,
              subject,
              sender,
              received_date,
              body_preview,
              body_content,
              body_type,
              created_at
            FROM email_cache
            """
        )

    cursor.execute("DROP TABLE email_cache")
    cursor.execute("ALTER TABLE email_cache_new RENAME TO email_cache")
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_email_cache_email_folder ON email_cache(email, folder)"
    )
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_email_cache_message_id ON email_cache(message_id)"
    )
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_email_cache_email_folder_message_id ON email_cache(email, folder, message_id)"
    )

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
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_email_cache_meta_checked_at ON email_cache_meta(last_checked_at)"
    )
