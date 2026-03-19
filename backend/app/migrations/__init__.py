#!/usr/bin/env python3
"""
轻量级数据库迁移框架

通过在应用启动阶段执行 register_migration 注册的迁移函数，保证数据库 schema 可演进。
"""

from __future__ import annotations

import logging
import sqlite3
from collections.abc import Callable
from dataclasses import dataclass

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


_REGISTRY: list[Migration] = []


def register_migration(version: str, description: str):
    """注册迁移函数的装饰器"""

    def decorator(func: Callable[[sqlite3.Connection], None]):
        _REGISTRY.append(Migration(version=version, description=description, handler=func))
        return func

    return decorator


def _normalize_registry(registry: list[Migration]) -> list[Migration]:
    """按照版本排序并去重"""
    seen: set[str] = set()
    ordered: list[Migration] = []
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


@register_migration("2026012001", "添加软删除支持")
def _add_soft_delete_support(conn: sqlite3.Connection) -> None:
    """为 accounts 表添加软删除字段

    - 添加 deleted_at 字段用于标记软删除时间
    - 创建索引优化软删除查询
    """
    cursor = conn.cursor()

    # 若 accounts 表不存在，直接返回
    cursor.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='accounts'"
    )
    if not cursor.fetchone():
        return

    # 查询已有字段
    cursor.execute("PRAGMA table_info(accounts)")
    columns = {col[1] for col in cursor.fetchall()}

    if "deleted_at" not in columns:
        cursor.execute(
            "ALTER TABLE accounts ADD COLUMN deleted_at TIMESTAMP DEFAULT NULL"
        )

    # 创建软删除索引
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_accounts_deleted_at ON accounts(deleted_at)"
    )

    # 创建复合索引优化常用查询（活跃账户）
    cursor.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_accounts_active 
        ON accounts(deleted_at, email) WHERE deleted_at IS NULL
        """
    )


@register_migration("2026012002", "优化数据库索引")
def _optimize_indexes(conn: sqlite3.Connection) -> None:
    """添加优化索引提升查询性能"""
    cursor = conn.cursor()

    # 检查 accounts 表是否存在
    cursor.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='accounts'"
    )
    accounts_exists = cursor.fetchone() is not None

    # 检查 email_cache 表是否存在
    cursor.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='email_cache'"
    )
    email_cache_exists = cursor.fetchone() is not None

    if accounts_exists:
        # 邮箱搜索（小写）
        try:
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_accounts_email_lower ON accounts(LOWER(email))"
            )
        except Exception:
            pass  # 某些 SQLite 版本可能不支持表达式索引

        # 使用状态 + 创建时间
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_accounts_is_used_created ON accounts(is_used, created_at)"
        )

        # 最后使用时间
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_accounts_last_used ON accounts(last_used_at DESC)"
        )

    if email_cache_exists:
        # 邮箱 + 接收时间
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_email_cache_email_received ON email_cache(email, received_date DESC)"
        )

        # 邮箱 + 文件夹 + 接收时间
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_email_cache_email_folder_received ON email_cache(email, folder, received_date DESC)"
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
        """
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


@register_migration("2026020100", "创建审计事件表")
def _create_audit_events_table(conn: sqlite3.Connection) -> None:
    """创建 audit_events 表用于记录安全相关事件"""
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS audit_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            event_type TEXT NOT NULL,
            timestamp TEXT NOT NULL,
            user_id TEXT,
            ip_address TEXT,
            user_agent TEXT,
            resource TEXT,
            action TEXT,
            details TEXT,
            success INTEGER NOT NULL DEFAULT 1,
            error_message TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # 创建索引优化查询
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_audit_events_type ON audit_events(event_type)"
    )
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_audit_events_timestamp ON audit_events(timestamp)"
    )
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_audit_events_user_id ON audit_events(user_id)"
    )
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_audit_events_ip ON audit_events(ip_address)"
    )
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_audit_events_type_timestamp ON audit_events(event_type, timestamp)"
    )

    logger.info("审计事件表创建完成")


@register_migration("2026020101", "将 JSON 标签转换为关系表")
def _migrate_tag_relations(conn: sqlite3.Connection) -> None:
    """将 JSON 格式的 account_tags 表转换为关系型 tags + account_tag_relations 表"""
    import json

    cursor = conn.cursor()

    # 检查 account_tags 表是否存在
    cursor.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='account_tags'"
    )
    if not cursor.fetchone():
        # 表不存在，直接创建新表结构
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS tags (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS account_tag_relations (
                account_email TEXT NOT NULL,
                tag_id INTEGER NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (account_email, tag_id),
                FOREIGN KEY (account_email) REFERENCES accounts(email) ON DELETE CASCADE,
                FOREIGN KEY (tag_id) REFERENCES tags(id) ON DELETE CASCADE
            )
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_atr_tag_id ON account_tag_relations(tag_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_atr_email ON account_tag_relations(account_email)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_tags_name ON tags(name)")
        return

    # 检查 account_tags_backup_json 是否已存在（说明迁移已执行过）
    cursor.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='account_tags_backup_json'"
    )
    if cursor.fetchone():
        return

    # 创建新表
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS tags (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS account_tag_relations (
            account_email TEXT NOT NULL,
            tag_id INTEGER NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (account_email, tag_id),
            FOREIGN KEY (account_email) REFERENCES accounts(email) ON DELETE CASCADE,
            FOREIGN KEY (tag_id) REFERENCES tags(id) ON DELETE CASCADE
        )
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_atr_tag_id ON account_tag_relations(tag_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_atr_email ON account_tag_relations(account_email)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_tags_name ON tags(name)")

    # 迁移数据
    cursor.execute("SELECT email, tags FROM account_tags")
    rows = cursor.fetchall()

    tag_cache: dict[str, int] = {}

    for row in rows:
        email = row[0] if not isinstance(row, sqlite3.Row) else row["email"]
        tags_json = row[1] if not isinstance(row, sqlite3.Row) else row["tags"]

        if not tags_json:
            continue

        try:
            tags = json.loads(tags_json)
        except json.JSONDecodeError:
            logger.warning(f"账户 {email} 的标签 JSON 解析失败，跳过")
            continue

        if not tags:
            continue

        for tag_name in tags:
            if not tag_name or not str(tag_name).strip():
                continue

            tag_name = str(tag_name).strip()

            if tag_name not in tag_cache:
                cursor.execute("INSERT OR IGNORE INTO tags (name) VALUES (?)", (tag_name,))
                cursor.execute("SELECT id FROM tags WHERE name = ?", (tag_name,))
                tag_row = cursor.fetchone()
                if tag_row:
                    tag_id = tag_row[0] if not isinstance(tag_row, sqlite3.Row) else tag_row["id"]
                    tag_cache[tag_name] = tag_id
                else:
                    continue

            cursor.execute("""
                INSERT OR IGNORE INTO account_tag_relations (account_email, tag_id)
                VALUES (?, ?)
            """, (email, tag_cache[tag_name]))

    # 重命名原表为备份
    cursor.execute("ALTER TABLE account_tags RENAME TO account_tags_backup_json")
    logger.info("标签数据已从 JSON 格式迁移到关系表")


@register_migration("2026030401", "为 accounts 表增加健康检测字段")
def _add_health_check_columns(conn: sqlite3.Connection) -> None:
    cursor = conn.cursor()
    cursor.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='accounts'"
    )
    if not cursor.fetchone():
        return

    cursor.execute("PRAGMA table_info(accounts)")
    columns = {col[1] for col in cursor.fetchall()}

    if "health_status" not in columns:
        cursor.execute(
            "ALTER TABLE accounts ADD COLUMN health_status TEXT DEFAULT 'unknown'"
        )
    if "last_health_check_at" not in columns:
        cursor.execute(
            "ALTER TABLE accounts ADD COLUMN last_health_check_at TIMESTAMP"
        )
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_accounts_health_status ON accounts(health_status)"
    )


@register_migration("2026030402", "创建验证码提取规则表")
def _create_extraction_rules_table(conn: sqlite3.Connection) -> None:
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS extraction_rules (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            sender_filter TEXT DEFAULT '',
            subject_filter TEXT DEFAULT '',
            regex_pattern TEXT NOT NULL,
            priority INTEGER DEFAULT 0,
            is_active INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_extraction_rules_active ON extraction_rules(is_active, priority DESC)"
    )


@register_migration("2026031901", "创建 Outlook 账户资产表")
def _create_outlook_accounts_table(conn: sqlite3.Connection) -> None:
    cursor = conn.cursor()
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS outlook_accounts (
            email TEXT PRIMARY KEY,
            status TEXT NOT NULL DEFAULT 'active',
            account_type TEXT NOT NULL DEFAULT 'consumer',
            source_account_email TEXT,
            default_channel_id INTEGER,
            notes TEXT DEFAULT '',
            last_synced_at TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (source_account_email) REFERENCES accounts(email) ON DELETE SET NULL
        )
        """
    )
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_outlook_accounts_status ON outlook_accounts(status)"
    )
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_outlook_accounts_source_email ON outlook_accounts(source_account_email)"
    )
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_outlook_accounts_default_channel_id ON outlook_accounts(default_channel_id)"
    )


@register_migration("2026031902", "创建 OAuth 配置表")
def _create_oauth_configs_table(conn: sqlite3.Connection) -> None:
    cursor = conn.cursor()
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS oauth_configs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            provider TEXT NOT NULL,
            name TEXT NOT NULL,
            client_id TEXT NOT NULL UNIQUE,
            client_secret TEXT DEFAULT '',
            tenant_id TEXT DEFAULT '',
            redirect_uri TEXT DEFAULT '',
            scopes TEXT DEFAULT '',
            authorization_url TEXT DEFAULT '',
            token_url TEXT DEFAULT '',
            status TEXT NOT NULL DEFAULT 'active',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_oauth_configs_provider_status ON oauth_configs(provider, status)"
    )


@register_migration("2026031903", "创建 OAuth Token 资产表")
def _create_oauth_tokens_table(conn: sqlite3.Connection) -> None:
    cursor = conn.cursor()
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS oauth_tokens (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            oauth_config_id INTEGER NOT NULL,
            email TEXT NOT NULL,
            access_token TEXT DEFAULT '',
            refresh_token TEXT DEFAULT '',
            expires_at TIMESTAMP,
            scopes_granted TEXT DEFAULT '',
            status TEXT NOT NULL DEFAULT 'active',
            last_error TEXT DEFAULT '',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (oauth_config_id) REFERENCES oauth_configs(id) ON DELETE CASCADE
        )
        """
    )
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_oauth_tokens_email_status ON oauth_tokens(email, status)"
    )
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_oauth_tokens_config_id ON oauth_tokens(oauth_config_id)"
    )
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_oauth_tokens_expires_at ON oauth_tokens(expires_at)"
    )


@register_migration("2026031904", "创建账户能力表")
def _create_account_capabilities_table(conn: sqlite3.Connection) -> None:
    cursor = conn.cursor()
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS account_capabilities (
            email TEXT PRIMARY KEY,
            imap_ready INTEGER NOT NULL DEFAULT 0,
            graph_ready INTEGER NOT NULL DEFAULT 0,
            protocol_ready INTEGER NOT NULL DEFAULT 0,
            browser_fallback_ready INTEGER NOT NULL DEFAULT 0,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (email) REFERENCES outlook_accounts(email) ON DELETE CASCADE
        )
        """
    )
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_account_capabilities_graph_ready ON account_capabilities(graph_ready)"
    )
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_account_capabilities_protocol_ready ON account_capabilities(protocol_ready)"
    )


@register_migration("2026031905", "创建账户资料缓存表")
def _create_account_profiles_cache_table(conn: sqlite3.Connection) -> None:
    cursor = conn.cursor()
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS account_profiles_cache (
            email TEXT PRIMARY KEY,
            profile_json TEXT NOT NULL DEFAULT '{}',
            synced_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (email) REFERENCES outlook_accounts(email) ON DELETE CASCADE
        )
        """
    )
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_account_profiles_cache_synced_at ON account_profiles_cache(synced_at)"
    )


@register_migration("2026031906", "创建账户安全方式快照表")
def _create_account_security_methods_snapshot_table(conn: sqlite3.Connection) -> None:
    cursor = conn.cursor()
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS account_security_methods_snapshot (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT NOT NULL,
            method_type TEXT NOT NULL,
            method_id TEXT NOT NULL,
            display_value TEXT DEFAULT '',
            status TEXT NOT NULL DEFAULT 'active',
            raw_json TEXT DEFAULT '{}',
            synced_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(email, method_type, method_id),
            FOREIGN KEY (email) REFERENCES outlook_accounts(email) ON DELETE CASCADE
        )
        """
    )
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_account_security_methods_email_type ON account_security_methods_snapshot(email, method_type)"
    )


@register_migration("2026031907", "创建辅助邮箱资源池表")
def _create_aux_email_resources_table(conn: sqlite3.Connection) -> None:
    cursor = conn.cursor()
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS aux_email_resources (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            address TEXT NOT NULL UNIQUE,
            provider TEXT NOT NULL DEFAULT 'custom',
            source_type TEXT NOT NULL DEFAULT 'manual',
            status TEXT NOT NULL DEFAULT 'available',
            channel_id INTEGER,
            fail_count INTEGER NOT NULL DEFAULT 0,
            last_email_id INTEGER,
            bound_account_email TEXT,
            notes TEXT DEFAULT '',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (bound_account_email) REFERENCES outlook_accounts(email) ON DELETE SET NULL
        )
        """
    )
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_aux_email_resources_status ON aux_email_resources(status)"
    )
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_aux_email_resources_channel_id ON aux_email_resources(channel_id)"
    )
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_aux_email_resources_bound_account_email ON aux_email_resources(bound_account_email)"
    )


@register_migration("2026031908", "创建渠道主表")
def _create_channels_table(conn: sqlite3.Connection) -> None:
    cursor = conn.cursor()
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS channels (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT NOT NULL UNIQUE,
            name TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'active',
            priority INTEGER NOT NULL DEFAULT 0,
            pick_strategy TEXT NOT NULL DEFAULT 'round_robin',
            cooldown_seconds INTEGER NOT NULL DEFAULT 0,
            notes TEXT DEFAULT '',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_channels_status_priority ON channels(status, priority DESC)"
    )


@register_migration("2026031909", "创建渠道与账户关系表")
def _create_channel_account_relations_table(conn: sqlite3.Connection) -> None:
    cursor = conn.cursor()
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS channel_account_relations (
            channel_id INTEGER NOT NULL,
            account_email TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'active',
            weight INTEGER NOT NULL DEFAULT 100,
            last_assigned_at TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (channel_id, account_email),
            FOREIGN KEY (channel_id) REFERENCES channels(id) ON DELETE CASCADE,
            FOREIGN KEY (account_email) REFERENCES outlook_accounts(email) ON DELETE CASCADE
        )
        """
    )
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_channel_account_relations_email ON channel_account_relations(account_email)"
    )
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_channel_account_relations_status ON channel_account_relations(status)"
    )


@register_migration("2026031910", "创建渠道与资源关系表")
def _create_channel_resource_relations_table(conn: sqlite3.Connection) -> None:
    cursor = conn.cursor()
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS channel_resource_relations (
            channel_id INTEGER NOT NULL,
            resource_id INTEGER NOT NULL,
            status TEXT NOT NULL DEFAULT 'active',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (channel_id, resource_id),
            FOREIGN KEY (channel_id) REFERENCES channels(id) ON DELETE CASCADE,
            FOREIGN KEY (resource_id) REFERENCES aux_email_resources(id) ON DELETE CASCADE
        )
        """
    )
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_channel_resource_relations_status ON channel_resource_relations(status)"
    )


@register_migration("2026031911", "创建取号租约表")
def _create_allocation_leases_table(conn: sqlite3.Connection) -> None:
    cursor = conn.cursor()
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS allocation_leases (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            channel_id INTEGER NOT NULL,
            account_email TEXT NOT NULL,
            leased_to TEXT DEFAULT '',
            leased_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            expires_at TIMESTAMP NOT NULL,
            status TEXT NOT NULL DEFAULT 'active',
            released_at TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (channel_id) REFERENCES channels(id) ON DELETE CASCADE,
            FOREIGN KEY (account_email) REFERENCES outlook_accounts(email) ON DELETE CASCADE
        )
        """
    )
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_allocation_leases_channel_status ON allocation_leases(channel_id, status)"
    )
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_allocation_leases_expires_at ON allocation_leases(expires_at)"
    )
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_allocation_leases_account_email ON allocation_leases(account_email)"
    )


@register_migration("2026031912", "创建协议任务主表")
def _create_protocol_tasks_table(conn: sqlite3.Connection) -> None:
    cursor = conn.cursor()
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS protocol_tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            task_type TEXT NOT NULL,
            target_email TEXT NOT NULL,
            old_email TEXT DEFAULT '',
            new_email TEXT DEFAULT '',
            verification_email TEXT DEFAULT '',
            channel_id INTEGER,
            resource_id INTEGER,
            status TEXT NOT NULL DEFAULT 'pending',
            retry_count INTEGER NOT NULL DEFAULT 0,
            error_message TEXT DEFAULT '',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_protocol_tasks_status ON protocol_tasks(status)"
    )
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_protocol_tasks_type ON protocol_tasks(task_type)"
    )
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_protocol_tasks_target_email ON protocol_tasks(target_email)"
    )


@register_migration("2026031913", "创建协议任务步骤表")
def _create_protocol_task_steps_table(conn: sqlite3.Connection) -> None:
    cursor = conn.cursor()
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS protocol_task_steps (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            task_id INTEGER NOT NULL,
            step TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'pending',
            detail TEXT DEFAULT '',
            started_at TIMESTAMP,
            finished_at TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (task_id) REFERENCES protocol_tasks(id) ON DELETE CASCADE
        )
        """
    )
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_protocol_task_steps_task_id ON protocol_task_steps(task_id)"
    )
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_protocol_task_steps_status ON protocol_task_steps(status)"
    )


@register_migration("2026031914", "创建账户操作审计表")
def _create_account_operation_audit_table(conn: sqlite3.Connection) -> None:
    cursor = conn.cursor()
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS account_operation_audit (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT NOT NULL,
            operation TEXT NOT NULL,
            operator TEXT DEFAULT '',
            result TEXT NOT NULL DEFAULT 'success',
            details TEXT DEFAULT '',
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (email) REFERENCES outlook_accounts(email) ON DELETE CASCADE
        )
        """
    )
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_account_operation_audit_email ON account_operation_audit(email)"
    )
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_account_operation_audit_operation ON account_operation_audit(operation)"
    )
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_account_operation_audit_timestamp ON account_operation_audit(timestamp)"
    )


@register_migration("2026031915", "补充 Outlook 重构高频索引")
def _add_outlook_refactor_indexes(conn: sqlite3.Connection) -> None:
    cursor = conn.cursor()
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_aux_email_resources_channel_status ON aux_email_resources(channel_id, status)"
    )
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_channel_account_relations_channel_status ON channel_account_relations(channel_id, status)"
    )
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_account_security_methods_email_status ON account_security_methods_snapshot(email, status)"
    )
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_protocol_tasks_channel_status ON protocol_tasks(channel_id, status)"
    )
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_protocol_tasks_status_updated_at ON protocol_tasks(status, updated_at)"
    )


@register_migration("2026031916", "为渠道表增加代理配置字段")
def _add_channel_proxy_columns(conn: sqlite3.Connection) -> None:
    cursor = conn.cursor()
    cursor.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='channels'"
    )
    if not cursor.fetchone():
        return

    cursor.execute("PRAGMA table_info(channels)")
    columns = {col[1] for col in cursor.fetchall()}

    if "proxy_url" not in columns:
        cursor.execute("ALTER TABLE channels ADD COLUMN proxy_url TEXT DEFAULT ''")
    if "proxy_group" not in columns:
        cursor.execute("ALTER TABLE channels ADD COLUMN proxy_group TEXT DEFAULT ''")

    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_channels_proxy_group ON channels(proxy_group)"
    )
