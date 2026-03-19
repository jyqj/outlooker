#!/usr/bin/env python3
"""
回填 Outlook 账户资产表。

用途：
- 将旧 `accounts` 表中存在 refresh_token 的记录迁移到 `outlook_accounts`
- 避免在应用启动阶段做隐式数据修复
- 可重复执行，已存在记录会自动跳过
"""

from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT / "backend"))

from app.migrations import apply_migrations
from app.settings import get_settings


def _resolve_db_path() -> Path:
    settings = get_settings()
    db_path = Path(settings.database_path)
    if not db_path.is_absolute():
        db_path = PROJECT_ROOT / db_path
    return db_path


def _table_columns(cursor: sqlite3.Cursor, table_name: str) -> set[str]:
    cursor.execute(f"PRAGMA table_info({table_name})")
    return {row[1] for row in cursor.fetchall()}


def main() -> int:
    db_path = _resolve_db_path()
    if not db_path.exists():
        print(f"数据库不存在: {db_path}")
        return 1

    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    try:
        apply_migrations(conn)
        cursor = conn.cursor()

        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='accounts'"
        )
        if not cursor.fetchone():
            print("未找到 accounts 表，无需回填")
            return 0

        columns = _table_columns(cursor, "accounts")
        where_clauses = ["refresh_token IS NOT NULL", "refresh_token != ''"]
        if "deleted_at" in columns:
            where_clauses.append("deleted_at IS NULL")

        query = f"""
            SELECT email
            FROM accounts
            WHERE {' AND '.join(where_clauses)}
            ORDER BY email ASC
        """
        cursor.execute(query)
        rows = cursor.fetchall()

        inserted = 0
        skipped = 0
        for row in rows:
            email = row["email"]
            cursor.execute(
                """
                INSERT OR IGNORE INTO outlook_accounts (
                    email, status, account_type, source_account_email, notes
                ) VALUES (?, 'active', 'consumer', ?, 'backfilled from accounts')
                """,
                (email, email),
            )
            if cursor.rowcount > 0:
                inserted += 1
            else:
                skipped += 1

        conn.commit()
        total = len(rows)
        print(f"扫描到账户: {total}")
        print(f"新增回填: {inserted}")
        print(f"已存在跳过: {skipped}")
        return 0
    finally:
        conn.close()


if __name__ == "__main__":
    raise SystemExit(main())
