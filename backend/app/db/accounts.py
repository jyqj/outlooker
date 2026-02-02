#!/usr/bin/env python3
"""
Account CRUD operations module.

Handles all account-related database operations including:
- Account creation, reading, updating, and deletion
- Account tags management
- Account usage tracking
"""

import json
import logging
import random
import sqlite3
from typing import Any

from ..auth.security import decrypt_if_needed, encrypt_if_needed
from ..settings import get_settings
from .base import RunInThreadMixin

logger = logging.getLogger(__name__)
_settings = get_settings()
CLIENT_ID = _settings.client_id


class AccountsMixin(RunInThreadMixin):
    """Mixin providing account-related database operations.
    
    标签方法已迁移为使用关系表实现（TagsMixin._v2 方法）。
    此处的方法作为向后兼容的接口，内部委托给 v2 方法。
    """

    async def get_account_tags(self, email: str) -> list[str]:
        """Get tags for an account.
        
        已迁移为使用关系表实现。
        """
        # 委托给 v2 方法（使用关系表）
        return await self.get_account_tags_v2(email)

    async def set_account_tags(self, email: str, tags: list[str]) -> bool:
        """Set tags for an account.
        
        已迁移为使用关系表实现。
        """
        # 委托给 v2 方法（使用关系表）
        return await self.set_account_tags_v2(email, tags)

    async def get_all_tags(self) -> list[str]:
        """Get all unique tags across all accounts.
        
        已迁移为使用关系表实现。
        """
        # 委托给 v2 方法（使用关系表）
        return await self.get_all_tags_v2()

    async def get_accounts_with_tags(self) -> dict[str, list[str]]:
        """Get all accounts with their tags.
        
        已迁移为使用关系表实现。
        """

        def _sync_get(conn: sqlite3.Connection) -> dict[str, list[str]]:
            cursor = conn.cursor()
            # 使用关系表查询
            cursor.execute("""
                SELECT atr.account_email, GROUP_CONCAT(t.name, ',') as tags
                FROM account_tag_relations atr
                JOIN tags t ON atr.tag_id = t.id
                GROUP BY atr.account_email
            """)
            rows = cursor.fetchall()

            result = {}
            for row in rows:
                email = row[0]
                tags_str = row[1]
                result[email] = tags_str.split(',') if tags_str else []

            return result

        return await self._run_in_thread(_sync_get)

    async def get_all_accounts(self) -> dict[str, dict[str, str]]:
        """Get all accounts (excluding soft-deleted)."""

        def _sync_get(conn: sqlite3.Connection) -> dict[str, dict[str, str]]:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT email, password, client_id, refresh_token, is_used, last_used_at
                FROM accounts
                WHERE deleted_at IS NULL
                """
            )
            rows = cursor.fetchall()

            result = {}
            for row in rows:
                result[row["email"]] = {
                    "password": row["password"] or "",
                    "client_id": row["client_id"] or CLIENT_ID,
                    "refresh_token": row["refresh_token"],
                    "is_used": bool(row["is_used"]) if row["is_used"] is not None else False,
                    "last_used_at": row["last_used_at"],
                }
            return result

        return await self._run_in_thread(_sync_get)

    async def get_first_unused_account_email(self) -> str | None:
        """
        Get the first unused account email (sorted by creation time).

        Returns None if no unused accounts exist.
        """

        def _sync_get(conn: sqlite3.Connection) -> str | None:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT email
                FROM accounts
                WHERE is_used = 0 AND deleted_at IS NULL
                ORDER BY created_at ASC
                LIMIT 1
                """
            )
            row = cursor.fetchone()
            return row["email"] if row else None

        return await self._run_in_thread(_sync_get)

    async def mark_account_used(self, email: str) -> bool:
        """Mark an account as used and record the last used time."""

        def _sync_mark(conn: sqlite3.Connection) -> bool:
            try:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    UPDATE accounts
                    SET is_used = 1,
                        last_used_at = CURRENT_TIMESTAMP,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE email = ? AND deleted_at IS NULL
                    """,
                    (email,),
                )
                conn.commit()
                return cursor.rowcount > 0
            except Exception as e:
                logger.error(f"标记账户为已使用失败: {e}")
                return False

        return await self._run_in_thread(_sync_mark)

    async def replace_all_accounts(self, accounts: dict[str, dict[str, str]]) -> bool:
        """Replace all accounts with the provided data."""

        def _sync_replace(conn: sqlite3.Connection) -> bool:
            cursor = conn.cursor()
            try:
                cursor.execute("DELETE FROM accounts")
                entries = []
                for email, info in accounts.items():
                    entries.append(
                        (
                            email,
                            encrypt_if_needed(info.get("password", "")),
                            info.get("client_id", CLIENT_ID),
                            encrypt_if_needed(info.get("refresh_token", "")),
                        )
                    )

                if entries:
                    cursor.executemany(
                        "INSERT INTO accounts (email, password, client_id, refresh_token) VALUES (?, ?, ?, ?)",
                        entries,
                    )
                conn.commit()
                return True
            except Exception as e:
                logger.error(f"替换账户数据失败: {e}")
                conn.rollback()
                return False

        return await self._run_in_thread(_sync_replace)

    async def add_account(
        self, email: str, password: str = "", client_id: str = "", refresh_token: str = ""
    ) -> bool:
        """Add a new account."""

        def _sync_add(conn: sqlite3.Connection) -> bool:
            try:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    INSERT INTO accounts (email, password, client_id, refresh_token)
                    VALUES (?, ?, ?, ?)
                    """,
                    (
                        email,
                        encrypt_if_needed(password or ""),
                        client_id or CLIENT_ID,
                        encrypt_if_needed(refresh_token or ""),
                    ),
                )
                conn.commit()
                return True
            except sqlite3.IntegrityError:
                return False
            except Exception as e:
                logger.error(f"添加账户失败: {e}")
                return False

        return await self._run_in_thread(_sync_add)

    async def update_account(
        self,
        email: str,
        password: str | None = None,
        client_id: str | None = None,
        refresh_token: str | None = None,
    ) -> bool:
        """Update an existing account."""

        def _sync_update(conn: sqlite3.Connection) -> bool:
            try:
                cursor = conn.cursor()

                updates = []
                params = []

                if password is not None:
                    updates.append("password = ?")
                    params.append(encrypt_if_needed(password or ""))

                if client_id is not None:
                    updates.append("client_id = ?")
                    params.append(client_id)

                if refresh_token is not None:
                    updates.append("refresh_token = ?")
                    params.append(encrypt_if_needed(refresh_token or ""))

                if not updates:
                    return True

                updates.append("updated_at = CURRENT_TIMESTAMP")
                params.append(email)

                sql = f"UPDATE accounts SET {', '.join(updates)} WHERE email = ? AND deleted_at IS NULL"
                cursor.execute(sql, params)
                conn.commit()
                return cursor.rowcount > 0
            except Exception as e:
                logger.error(f"更新账户失败: {e}")
                return False

        return await self._run_in_thread(_sync_update)

    async def delete_account(self, email: str) -> bool:
        """Delete an account and its related data."""

        def _sync_delete(conn: sqlite3.Connection) -> bool:
            try:
                cursor = conn.cursor()

                cursor.execute("DELETE FROM accounts WHERE email = ?", (email,))
                account_deleted = cursor.rowcount > 0

                cursor.execute("DELETE FROM account_tags WHERE email = ?", (email,))
                cursor.execute("DELETE FROM email_cache WHERE email = ?", (email,))
                cursor.execute("DELETE FROM email_cache_meta WHERE email = ?", (email,))

                conn.commit()
                return account_deleted
            except Exception as e:
                logger.error(f"删除账户失败: {e}")
                return False

        return await self._run_in_thread(_sync_delete)

    async def batch_delete_accounts(self, emails: list[str]) -> tuple[int, int]:
        """
        批量删除账户（物理删除）。

        性能优化：使用 IN 子句批量 SQL 替代逐条处理
        ============================================================
        原理：
        - 逐条 DELETE 需要 N 次 SQL 执行，每次都有解析和执行开销
        - 批量 IN 子句只需 1 次 SQL 执行，数据库内部批量处理
        - 性能提升：O(n) 次数据库往返 -> O(1) 次
        - 对于 100 条记录，性能提升约 10x-50x
        
        注意：
        - 使用物理删除，同时清理关联数据
        - 对于大批量（>1000），建议分批处理避免 SQL 语句过长

        Returns:
            (deleted_count, failed_count) 元组
        """
        if not emails:
            return 0, 0

        def _sync_batch_delete(conn: sqlite3.Connection) -> tuple[int, int]:
            cursor = conn.cursor()

            try:
                # 使用 IN 子句批量删除
                placeholders = ",".join(["?"] * len(emails))

                # 1. 删除账户记录
                cursor.execute(f"""
                    DELETE FROM accounts WHERE email IN ({placeholders})
                """, emails)
                deleted = cursor.rowcount

                # 2. 批量清理关联数据（即使账户不存在也不会报错）
                cursor.execute(f"""
                    DELETE FROM account_tags WHERE email IN ({placeholders})
                """, emails)
                
                cursor.execute(f"""
                    DELETE FROM email_cache WHERE email IN ({placeholders})
                """, emails)
                
                cursor.execute(f"""
                    DELETE FROM email_cache_meta WHERE email IN ({placeholders})
                """, emails)

                # 3. 清理关系表中的标签关联
                cursor.execute(f"""
                    DELETE FROM account_tag_relations WHERE account_email IN ({placeholders})
                """, emails)

                conn.commit()
                
                failed = len(emails) - deleted
                logger.info(f"批量删除 {deleted} 个账户，{failed} 个不存在或已删除")
                return deleted, failed

            except Exception as e:
                logger.error(f"批量删除失败: {e}")
                conn.rollback()
                return 0, len(emails)

        return await self._run_in_thread(_sync_batch_delete)

    async def batch_update_tags(
        self, emails: list[str], tags: list[str], action: str = "set"
    ) -> tuple[int, int]:
        """
        批量更新账户标签。

        已迁移为使用关系表实现（委托给 batch_update_tags_v2）。

        Args:
            emails: 邮箱列表
            tags: 标签列表
            action: "set" 替换所有标签, "add" 添加标签, "remove" 移除标签

        Returns:
            (updated_count, failed_count) 元组
        """
        # 委托给 v2 方法（使用关系表）
        return await self.batch_update_tags_v2(emails, tags, action)

    async def account_exists(self, email: str) -> bool:
        """Check if an account exists (excluding soft-deleted)."""

        def _sync_check(conn: sqlite3.Connection) -> bool:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT 1 FROM accounts WHERE email = ? AND deleted_at IS NULL", 
                (email,)
            )
            return cursor.fetchone() is not None

        return await self._run_in_thread(_sync_check)

    async def get_account(self, email: str) -> dict[str, Any] | None:
        """Get a single account's information (excluding soft-deleted)."""

        def _sync_get(conn: sqlite3.Connection) -> dict[str, Any] | None:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT password, client_id, refresh_token, is_used, last_used_at
                FROM accounts
                WHERE email = ? AND deleted_at IS NULL
                """,
                (email,),
            )
            row = cursor.fetchone()
            if row:
                return {
                    "password": decrypt_if_needed(row["password"]) if row["password"] else "",
                    "client_id": row["client_id"] or CLIENT_ID,
                    "refresh_token": (
                        decrypt_if_needed(row["refresh_token"]) if row["refresh_token"] else ""
                    ),
                    "is_used": bool(row["is_used"]) if row["is_used"] is not None else False,
                    "last_used_at": row["last_used_at"],
                }
            return None

        return await self._run_in_thread(_sync_get)

    async def migrate_from_config_file(self, config_file_path: str = "config.txt") -> tuple[int, int]:
        """Migrate data from config.txt to the database."""

        def _sync_migrate(conn: sqlite3.Connection) -> tuple[int, int]:
            import os

            if not os.path.exists(config_file_path):
                return 0, 0

            cursor = conn.cursor()
            added_count = 0
            error_count = 0

            try:
                with open(config_file_path, encoding="utf-8") as f:
                    lines = f.readlines()

                for line in lines:
                    line = line.strip()
                    if line.startswith("#") or not line:
                        continue

                    try:
                        parts = line.split("----")
                        if len(parts) >= 4:
                            email = parts[0].strip()
                            password = parts[1].strip()
                            refresh_token = parts[2].strip()
                            cid = parts[3].strip() or CLIENT_ID

                            cursor.execute("SELECT 1 FROM accounts WHERE email = ?", (email,))
                            if not cursor.fetchone():
                                cursor.execute(
                                    """
                                    INSERT INTO accounts (email, password, client_id, refresh_token)
                                    VALUES (?, ?, ?, ?)
                                    """,
                                    (
                                        email,
                                        encrypt_if_needed(password or ""),
                                        cid,
                                        encrypt_if_needed(refresh_token or ""),
                                    ),
                                )
                                added_count += 1
                        elif len(parts) == 2:
                            email = parts[0].strip()
                            refresh_token = parts[1].strip()
                            cursor.execute("SELECT 1 FROM accounts WHERE email = ?", (email,))
                            if not cursor.fetchone():
                                cursor.execute(
                                    """
                                    INSERT INTO accounts (email, password, client_id, refresh_token)
                                    VALUES (?, ?, ?, ?)
                                    """,
                                    (
                                        email,
                                        "",
                                        CLIENT_ID,
                                        encrypt_if_needed(refresh_token or ""),
                                    ),
                                )
                                added_count += 1
                        else:
                            error_count += 1
                            logger.error(f"迁移行格式错误（需要2或4个字段）: {line}")
                    except Exception as e:
                        logger.error(f"迁移行失败: {line}, 错误: {e}")
                        error_count += 1

                conn.commit()
                return added_count, error_count

            except Exception as e:
                logger.error(f"迁移配置文件失败: {e}")
                return 0, 1

        return await self._run_in_thread(_sync_migrate)

    async def get_random_account_without_tag(
        self,
        tag: str,
        exclude_tags: list[str] | None = None,
    ) -> dict[str, Any] | None:
        """
        随机获取一个没有指定标签的账户。

        已迁移为使用关系表实现（委托给 get_random_account_by_tag_filter_v2）。
        
        Args:
            tag: 目标标签（账户不能有此标签）
            exclude_tags: 额外排除的标签列表（账户不能有这些标签中的任何一个）

        Returns:
            账户信息字典，包含 email, password, client_id, refresh_token, tags
            如果没有符合条件的账户则返回 None
        """
        # 构建排除标签集合
        all_exclude_tags = [tag]
        if exclude_tags:
            all_exclude_tags.extend(exclude_tags)
        
        # 委托给 v2 方法（使用关系表）
        result = await self.get_random_account_by_tag_filter_v2(
            include_tag=None,
            exclude_tags=all_exclude_tags,
        )
        
        if result:
            # v2 方法返回的敏感字段需要解密
            return {
                "email": result["email"],
                "password": decrypt_if_needed(result["password"]) if result["password"] else "",
                "client_id": result["client_id"] or CLIENT_ID,
                "refresh_token": (
                    decrypt_if_needed(result["refresh_token"]) if result["refresh_token"] else ""
                ),
                "tags": result.get("tags", []),
            }
        return None

    async def get_tag_statistics(self) -> dict[str, Any]:
        """
        获取标签使用统计。

        已迁移为使用关系表实现（委托给 get_tag_statistics_v2）。

        Returns:
            包含以下字段的字典：
            - total_accounts: 总账户数
            - tagged_accounts: 有标签的账户数
            - untagged_accounts: 无标签的账户数
            - tags: 标签列表，每个标签包含 name, count, percentage
        """
        # 委托给 v2 方法（使用关系表）
        return await self.get_tag_statistics_v2()

    async def delete_tag_globally(self, tag_name: str) -> int:
        """
        从所有账户中删除指定标签。

        已迁移为使用关系表实现（委托给 delete_tag_globally_v2）。

        Args:
            tag_name: 要删除的标签名

        Returns:
            受影响的账户数量
        """
        # 委托给 v2 方法（使用关系表）
        return await self.delete_tag_globally_v2(tag_name)

    # ============================================================================
    # 软删除相关方法
    # ============================================================================

    async def soft_delete_account(self, email: str) -> bool:
        """软删除账户"""

        def _sync_delete(conn: sqlite3.Connection) -> bool:
            try:
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE accounts 
                    SET deleted_at = CURRENT_TIMESTAMP,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE email = ? AND deleted_at IS NULL
                """, (email,))
                conn.commit()
                return cursor.rowcount > 0
            except Exception as e:
                logger.error(f"软删除账户失败: {e}")
                return False

        return await self._run_in_thread(_sync_delete)

    async def restore_account(self, email: str) -> bool:
        """恢复已删除的账户"""

        def _sync_restore(conn: sqlite3.Connection) -> bool:
            try:
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE accounts 
                    SET deleted_at = NULL,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE email = ? AND deleted_at IS NOT NULL
                """, (email,))
                conn.commit()
                return cursor.rowcount > 0
            except Exception as e:
                logger.error(f"恢复账户失败: {e}")
                return False

        return await self._run_in_thread(_sync_restore)

    async def get_deleted_accounts(
        self, 
        page: int = 1, 
        page_size: int = 20
    ) -> tuple[list[dict], int]:
        """获取已删除的账户列表"""

        def _sync_get(conn: sqlite3.Connection) -> tuple[list[dict], int]:
            cursor = conn.cursor()

            # 总数
            cursor.execute("""
                SELECT COUNT(*) FROM accounts WHERE deleted_at IS NOT NULL
            """)
            total = cursor.fetchone()[0]

            # 分页查询
            offset = (page - 1) * page_size
            cursor.execute("""
                SELECT email, deleted_at, created_at
                FROM accounts
                WHERE deleted_at IS NOT NULL
                ORDER BY deleted_at DESC
                LIMIT ? OFFSET ?
            """, (page_size, offset))

            results = []
            for row in cursor.fetchall():
                results.append({
                    "email": row[0],
                    "deleted_at": row[1],
                    "created_at": row[2],
                })

            return results, total

        return await self._run_in_thread(_sync_get)

    async def permanently_delete_account(self, email: str) -> bool:
        """永久删除账户（物理删除）"""
        # 调用原有的 delete_account 方法
        return await self.delete_account(email)

    async def cleanup_deleted_accounts(self, days: int = 30) -> int:
        """清理超过指定天数的已删除账户"""

        def _sync_cleanup(conn: sqlite3.Connection) -> int:
            try:
                cursor = conn.cursor()
                cursor.execute("""
                    DELETE FROM accounts
                    WHERE deleted_at IS NOT NULL
                    AND deleted_at < datetime('now', ?)
                """, (f'-{days} days',))

                deleted = cursor.rowcount
                conn.commit()
                logger.info(f"清理了 {deleted} 个超过 {days} 天的已删除账户")
                return deleted
            except Exception as e:
                logger.error(f"清理已删除账户失败: {e}")
                return 0

        return await self._run_in_thread(_sync_cleanup)

    async def batch_soft_delete_accounts(self, emails: list[str]) -> tuple[int, int]:
        """
        批量软删除账户。

        性能优化：使用 IN 子句批量 UPDATE 替代逐条处理
        ============================================================
        原理：
        - 逐条 UPDATE 需要 N 次 SQL 执行
        - 批量 IN 子句只需 1 次 SQL 执行
        - 性能提升：O(n) -> O(1) 数据库往返次数
        
        软删除优势：
        - 数据可恢复，支持审计追溯
        - 外键关系保持完整
        - 相比物理删除更安全

        Returns:
            (deleted_count, failed_count) 元组
        """
        if not emails:
            return 0, 0

        def _sync_batch_delete(conn: sqlite3.Connection) -> tuple[int, int]:
            cursor = conn.cursor()

            try:
                # 使用 IN 子句批量软删除
                placeholders = ",".join(["?"] * len(emails))

                cursor.execute(f"""
                    UPDATE accounts 
                    SET deleted_at = CURRENT_TIMESTAMP,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE email IN ({placeholders})
                    AND deleted_at IS NULL
                """, emails)

                deleted = cursor.rowcount
                failed = len(emails) - deleted

                conn.commit()
                logger.info(f"批量软删除 {deleted} 个账户")
                return deleted, failed

            except Exception as e:
                logger.error(f"批量软删除失败: {e}")
                conn.rollback()
                return 0, len(emails)

        return await self._run_in_thread(_sync_batch_delete)

    async def rename_tag_globally(self, old_name: str, new_name: str) -> int:
        """
        重命名标签（在所有账户中）。

        已迁移为使用关系表实现（委托给 rename_tag_globally_v2）。

        Args:
            old_name: 原标签名
            new_name: 新标签名

        Returns:
            受影响的账户数量
        """
        # 委托给 v2 方法（使用关系表）
        return await self.rename_tag_globally_v2(old_name, new_name)

    async def get_accounts_by_tag_filter(
        self,
        tag: str | None = None,
        exclude_tags: list[str] | None = None,
        untagged_only: bool = False,
        search: str | None = None,
        page: int = 1,
        page_size: int = 10,
    ) -> tuple[list[dict[str, Any]], int]:
        """
        按标签条件筛选账户。

        已迁移为使用关系表实现（委托给 get_accounts_by_tag_filter_v2）。

        Args:
            tag: 筛选有此标签的账户
            exclude_tags: 排除有这些标签的账户
            untagged_only: 仅显示无标签账户
            search: 邮箱搜索关键词
            page: 页码
            page_size: 每页数量

        Returns:
            (账户列表, 总数)
        """
        # 委托给 v2 方法（使用关系表）
        return await self.get_accounts_by_tag_filter_v2(
            tag=tag,
            exclude_tags=exclude_tags,
            untagged_only=untagged_only,
            search=search,
            page=page,
            page_size=page_size,
        )
