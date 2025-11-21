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

from ..config import DEFAULT_EMAIL_LIMIT

logger = logging.getLogger(__name__)


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

