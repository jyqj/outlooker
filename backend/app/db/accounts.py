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
import sqlite3
from typing import Any

from ..auth.security import decrypt_if_needed, encrypt_if_needed
from ..settings import get_settings
from .base import RunInThreadMixin

logger = logging.getLogger(__name__)
_settings = get_settings()
CLIENT_ID = _settings.client_id


class AccountsMixin(RunInThreadMixin):
    """Mixin providing account-related database operations."""

    async def get_account_tags(self, email: str) -> list[str]:
        """Get tags for an account."""

        def _sync_get(conn: sqlite3.Connection) -> list[str]:
            cursor = conn.cursor()
            cursor.execute("SELECT tags FROM account_tags WHERE email = ?", (email,))
            row = cursor.fetchone()
            if row:
                try:
                    return json.loads(row["tags"])
                except json.JSONDecodeError:
                    return []
            return []

        return await self._run_in_thread(_sync_get)

    async def set_account_tags(self, email: str, tags: list[str]) -> bool:
        """Set tags for an account."""

        def _sync_set(conn: sqlite3.Connection) -> bool:
            try:
                cursor = conn.cursor()
                tags_json = json.dumps(tags, ensure_ascii=False)

                cursor.execute("SELECT id FROM account_tags WHERE email = ?", (email,))
                existing_record = cursor.fetchone()

                if existing_record:
                    cursor.execute(
                        """
                        UPDATE account_tags 
                        SET tags = ?, updated_at = CURRENT_TIMESTAMP 
                        WHERE email = ?
                        """,
                        (tags_json, email),
                    )
                    logger.info(f"更新账户 {email} 的标签: {tags}")
                else:
                    cursor.execute(
                        """
                        INSERT INTO account_tags (email, tags, created_at, updated_at) 
                        VALUES (?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                        """,
                        (email, tags_json),
                    )
                    logger.info(f"为账户 {email} 创建新标签: {tags}")

                conn.commit()
                logger.info(f"成功保存账户 {email} 的标签")
                return True
            except Exception as e:
                logger.error(f"设置账户标签失败: {e}")
                conn.rollback()
                return False

        return await self._run_in_thread(_sync_set)

    async def get_all_tags(self) -> list[str]:
        """Get all unique tags across all accounts."""

        def _sync_get(conn: sqlite3.Connection) -> list[str]:
            cursor = conn.cursor()
            cursor.execute("SELECT tags FROM account_tags")
            rows = cursor.fetchall()

            all_tags = set()
            for row in rows:
                try:
                    tags = json.loads(row["tags"])
                    all_tags.update(tags)
                except json.JSONDecodeError:
                    continue

            return sorted(list(all_tags))

        return await self._run_in_thread(_sync_get)

    async def get_accounts_with_tags(self) -> dict[str, list[str]]:
        """Get all accounts with their tags."""

        def _sync_get(conn: sqlite3.Connection) -> dict[str, list[str]]:
            cursor = conn.cursor()
            cursor.execute("SELECT email, tags FROM account_tags")
            rows = cursor.fetchall()

            result = {}
            for row in rows:
                try:
                    tags = json.loads(row["tags"])
                    result[row["email"]] = tags
                except json.JSONDecodeError:
                    result[row["email"]] = []

            return result

        return await self._run_in_thread(_sync_get)

    async def get_all_accounts(self) -> dict[str, dict[str, str]]:
        """Get all accounts."""

        def _sync_get(conn: sqlite3.Connection) -> dict[str, dict[str, str]]:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT email, password, client_id, refresh_token, is_used, last_used_at
                FROM accounts
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
                WHERE is_used = 0
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
                    WHERE email = ?
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

                sql = f"UPDATE accounts SET {', '.join(updates)} WHERE email = ?"
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
        Delete multiple accounts at once.

        Returns a tuple of (deleted_count, failed_count).
        """

        def _sync_batch_delete(conn: sqlite3.Connection) -> tuple[int, int]:
            deleted = 0
            failed = 0
            cursor = conn.cursor()

            try:
                for email in emails:
                    try:
                        cursor.execute("DELETE FROM accounts WHERE email = ?", (email,))
                        if cursor.rowcount > 0:
                            cursor.execute("DELETE FROM account_tags WHERE email = ?", (email,))
                            cursor.execute("DELETE FROM email_cache WHERE email = ?", (email,))
                            cursor.execute("DELETE FROM email_cache_meta WHERE email = ?", (email,))
                            deleted += 1
                        else:
                            failed += 1
                    except Exception as e:
                        logger.error(f"批量删除账户失败 {email}: {e}")
                        failed += 1

                conn.commit()
            except Exception as e:
                logger.error(f"批量删除事务失败: {e}")
                conn.rollback()
                return 0, len(emails)

            return deleted, failed

        return await self._run_in_thread(_sync_batch_delete)

    async def batch_update_tags(
        self, emails: list[str], tags: list[str], action: str = "set"
    ) -> tuple[int, int]:
        """
        Update tags for multiple accounts at once.

        Args:
            emails: List of email addresses
            tags: List of tags to apply
            action: "set" to replace, "add" to append, "remove" to delete

        Returns a tuple of (updated_count, failed_count).
        """

        def _sync_batch_update(conn: sqlite3.Connection) -> tuple[int, int]:
            updated = 0
            failed = 0
            cursor = conn.cursor()

            try:
                for email in emails:
                    try:
                        # Get current tags
                        cursor.execute("SELECT tags FROM account_tags WHERE email = ?", (email,))
                        row = cursor.fetchone()
                        current_tags = []
                        if row:
                            try:
                                current_tags = json.loads(row["tags"])
                            except json.JSONDecodeError:
                                current_tags = []

                        # Apply action
                        if action == "set":
                            new_tags = tags
                        elif action == "add":
                            new_tags = list(set(current_tags + tags))
                        elif action == "remove":
                            new_tags = [t for t in current_tags if t not in tags]
                        else:
                            new_tags = tags

                        tags_json = json.dumps(new_tags, ensure_ascii=False)

                        if row:
                            cursor.execute(
                                """
                                UPDATE account_tags 
                                SET tags = ?, updated_at = CURRENT_TIMESTAMP 
                                WHERE email = ?
                                """,
                                (tags_json, email),
                            )
                        else:
                            cursor.execute(
                                """
                                INSERT INTO account_tags (email, tags, created_at, updated_at) 
                                VALUES (?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                                """,
                                (email, tags_json),
                            )
                        updated += 1
                    except Exception as e:
                        logger.error(f"批量更新标签失败 {email}: {e}")
                        failed += 1

                conn.commit()
            except Exception as e:
                logger.error(f"批量更新标签事务失败: {e}")
                conn.rollback()
                return 0, len(emails)

            return updated, failed

        return await self._run_in_thread(_sync_batch_update)

    async def account_exists(self, email: str) -> bool:
        """Check if an account exists."""

        def _sync_check(conn: sqlite3.Connection) -> bool:
            cursor = conn.cursor()
            cursor.execute("SELECT 1 FROM accounts WHERE email = ?", (email,))
            return cursor.fetchone() is not None

        return await self._run_in_thread(_sync_check)

    async def get_account(self, email: str) -> dict[str, Any] | None:
        """Get a single account's information."""

        def _sync_get(conn: sqlite3.Connection) -> dict[str, Any] | None:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT password, client_id, refresh_token, is_used, last_used_at
                FROM accounts
                WHERE email = ?
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

        使用 SQL 级 LEFT JOIN + 过滤 + ORDER BY RANDOM() LIMIT 1 优化，
        避免全量加载到 Python 内存。

        Args:
            tag: 目标标签（账户不能有此标签）
            exclude_tags: 额外排除的标签列表（账户不能有这些标签中的任何一个）

        Returns:
            账户信息字典，包含 email, password, client_id, refresh_token, tags
            如果没有符合条件的账户则返回 None
        """

        def _sync_get(conn: sqlite3.Connection) -> dict[str, Any] | None:
            cursor = conn.cursor()

            # 构建排除标签集合
            tags_to_exclude = [tag]
            if exclude_tags:
                tags_to_exclude.extend(exclude_tags)

            # 使用 SQL 级 LEFT JOIN + 过滤
            # 获取没有排除标签的账户，使用 ORDER BY RANDOM() LIMIT 1 随机选择
            # 由于 SQLite 存储 JSON 格式的标签，需要在 Python 中解析后判断
            # 但这里我们优化为：先用 SQL 过滤掉有标签记录的账户，再在应用层做精确过滤
            # 这样可以减少内存占用
            cursor.execute(
                """
                SELECT a.email, a.password, a.client_id, a.refresh_token, 
                       COALESCE(t.tags, '[]') as tags
                FROM accounts a
                LEFT JOIN account_tags t ON a.email = t.email
                ORDER BY RANDOM()
                """
            )

            # 流式处理：逐行检查直到找到符合条件的账户
            tags_to_exclude_set = set(tags_to_exclude)
            for row in cursor:
                try:
                    account_tags = json.loads(row["tags"]) if row["tags"] else []
                except json.JSONDecodeError:
                    account_tags = []

                # 检查是否有需要排除的标签
                if not set(account_tags).intersection(tags_to_exclude_set):
                    # 找到符合条件的账户
                    return {
                        "email": row["email"],
                        "password": decrypt_if_needed(row["password"]) if row["password"] else "",
                        "client_id": row["client_id"] or CLIENT_ID,
                        "refresh_token": (
                            decrypt_if_needed(row["refresh_token"]) if row["refresh_token"] else ""
                        ),
                        "tags": account_tags,
                    }

            return None

        return await self._run_in_thread(_sync_get)

    async def get_tag_statistics(self) -> dict[str, Any]:
        """
        获取标签使用统计。

        Returns:
            包含以下字段的字典：
            - total_accounts: 总账户数
            - tagged_accounts: 有标签的账户数
            - untagged_accounts: 无标签的账户数
            - tags: 标签列表，每个标签包含 name, count, percentage
        """

        def _sync_get(conn: sqlite3.Connection) -> dict[str, Any]:
            cursor = conn.cursor()

            # 获取总账户数
            cursor.execute("SELECT COUNT(*) as count FROM accounts")
            total_accounts = cursor.fetchone()["count"]

            # 获取所有账户标签
            cursor.execute("SELECT email, tags FROM account_tags")
            rows = cursor.fetchall()

            # 统计标签
            tag_counts: dict[str, int] = {}
            accounts_with_tags = set()

            for row in rows:
                try:
                    tags = json.loads(row["tags"])
                    if tags:  # 只有非空标签列表才算有标签
                        accounts_with_tags.add(row["email"])
                        for tag in tags:
                            tag_counts[tag] = tag_counts.get(tag, 0) + 1
                except json.JSONDecodeError:
                    continue

            tagged_accounts = len(accounts_with_tags)
            untagged_accounts = total_accounts - tagged_accounts

            # 构建标签统计列表
            tags_list = []
            for tag_name, count in sorted(tag_counts.items(), key=lambda x: -x[1]):
                percentage = round(count / total_accounts * 100, 1) if total_accounts > 0 else 0
                tags_list.append({
                    "name": tag_name,
                    "count": count,
                    "percentage": percentage,
                })

            return {
                "total_accounts": total_accounts,
                "tagged_accounts": tagged_accounts,
                "untagged_accounts": untagged_accounts,
                "tags": tags_list,
            }

        return await self._run_in_thread(_sync_get)

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

        优化策略：
        - 无标签过滤条件时：使用 SQL 级分页 (LIMIT/OFFSET)
        - 有标签过滤条件时：使用 LEFT JOIN 减少查询次数，流式处理

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
        has_tag_filter = tag is not None or exclude_tags or untagged_only

        def _sync_get(conn: sqlite3.Connection) -> tuple[list[dict[str, Any]], int]:
            cursor = conn.cursor()

            # 优化路径 1: 无标签过滤条件，使用 SQL 级分页
            if not has_tag_filter:
                # 构建搜索条件
                where_clause = ""
                params: list[Any] = []
                if search:
                    where_clause = "WHERE a.email LIKE ?"
                    params.append(f"%{search}%")

                # 获取总数
                count_sql = f"SELECT COUNT(*) as cnt FROM accounts a {where_clause}"
                cursor.execute(count_sql, params)
                total = cursor.fetchone()["cnt"]

                # SQL 级分页
                offset = (page - 1) * page_size
                query_sql = f"""
                    SELECT a.email, a.password, a.client_id, a.refresh_token, 
                           a.is_used, a.last_used_at, COALESCE(t.tags, '[]') as tags
                    FROM accounts a
                    LEFT JOIN account_tags t ON a.email = t.email
                    {where_clause}
                    ORDER BY a.email
                    LIMIT ? OFFSET ?
                """
                params.extend([page_size, offset])
                cursor.execute(query_sql, params)

                result = []
                for row in cursor.fetchall():
                    try:
                        tags_list = json.loads(row["tags"]) if row["tags"] else []
                    except json.JSONDecodeError:
                        tags_list = []

                    result.append({
                        "email": row["email"],
                        "password": row["password"] or "",
                        "client_id": row["client_id"] or CLIENT_ID,
                        "refresh_token": row["refresh_token"] or "",
                        "is_used": bool(row["is_used"]) if row["is_used"] is not None else False,
                        "last_used_at": row["last_used_at"],
                        "tags": tags_list,
                    })

                return result, total

            # 优化路径 2: 有标签过滤条件，使用 LEFT JOIN + 流式处理
            # 先用 SQL 做搜索过滤，减少数据量
            where_clause = ""
            params = []
            if search:
                where_clause = "WHERE a.email LIKE ?"
                params.append(f"%{search}%")

            cursor.execute(
                f"""
                SELECT a.email, a.password, a.client_id, a.refresh_token, 
                       a.is_used, a.last_used_at, COALESCE(t.tags, '[]') as tags
                FROM accounts a
                LEFT JOIN account_tags t ON a.email = t.email
                {where_clause}
                ORDER BY a.email
                """,
                params,
            )

            # 流式过滤
            filtered_results = []
            for row in cursor:
                try:
                    account_tags = json.loads(row["tags"]) if row["tags"] else []
                except json.JSONDecodeError:
                    account_tags = []

                # 仅无标签账户
                if untagged_only and account_tags:
                    continue

                # 必须有指定标签
                if tag and tag not in account_tags:
                    continue

                # 排除标签
                if exclude_tags and any(t in account_tags for t in exclude_tags):
                    continue

                filtered_results.append({
                    "email": row["email"],
                    "password": row["password"] or "",
                    "client_id": row["client_id"] or CLIENT_ID,
                    "refresh_token": row["refresh_token"] or "",
                    "is_used": bool(row["is_used"]) if row["is_used"] is not None else False,
                    "last_used_at": row["last_used_at"],
                    "tags": account_tags,
                })

            total = len(filtered_results)

            # 应用层分页
            start = (page - 1) * page_size
            end = start + page_size
            paged_results = filtered_results[start:end]

            return paged_results, total

        return await self._run_in_thread(_sync_get)
