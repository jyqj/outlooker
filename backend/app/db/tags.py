#!/usr/bin/env python3
"""
Tag database operations using relational tables.
"""

import logging
import random
import sqlite3
from typing import Any

from .base import RunInThreadMixin

logger = logging.getLogger(__name__)


class TagsMixin(RunInThreadMixin):
    """Mixin providing tag-related database operations using relational tables."""

    async def get_account_tags_v2(self, email: str) -> list[str]:
        """获取账户的标签列表（使用关系表）"""
        
        def _sync_get(conn: sqlite3.Connection) -> list[str]:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT t.name
                FROM tags t
                JOIN account_tag_relations atr ON t.id = atr.tag_id
                WHERE atr.account_email = ?
                ORDER BY t.name
            """, (email,))
            return [row[0] for row in cursor.fetchall()]
        
        return await self._run_in_thread(_sync_get)

    async def set_account_tags_v2(self, email: str, tags: list[str]) -> bool:
        """设置账户标签（完全替换）"""
        
        def _sync_set(conn: sqlite3.Connection) -> bool:
            try:
                cursor = conn.cursor()
                
                # 1. 删除现有关联
                cursor.execute("""
                    DELETE FROM account_tag_relations WHERE account_email = ?
                """, (email,))
                
                # 2. 添加新标签
                for tag_name in tags:
                    if not tag_name or not tag_name.strip():
                        continue
                    tag_name = tag_name.strip()
                    
                    # 确保标签存在
                    cursor.execute("""
                        INSERT OR IGNORE INTO tags (name) VALUES (?)
                    """, (tag_name,))
                    
                    # 获取标签 ID
                    cursor.execute("SELECT id FROM tags WHERE name = ?", (tag_name,))
                    tag_row = cursor.fetchone()
                    if not tag_row:
                        continue
                    
                    # 创建关联
                    cursor.execute("""
                        INSERT OR IGNORE INTO account_tag_relations (account_email, tag_id)
                        VALUES (?, ?)
                    """, (email, tag_row[0]))
                
                conn.commit()
                return True
            except Exception as e:
                logger.error(f"设置账户标签失败: {e}")
                conn.rollback()
                return False
        
        return await self._run_in_thread(_sync_set)

    async def add_tags_to_account(self, email: str, tags: list[str]) -> bool:
        """为账户添加标签（不影响现有标签）"""
        
        def _sync_add(conn: sqlite3.Connection) -> bool:
            try:
                cursor = conn.cursor()
                
                for tag_name in tags:
                    if not tag_name or not tag_name.strip():
                        continue
                    tag_name = tag_name.strip()
                    
                    cursor.execute("""
                        INSERT OR IGNORE INTO tags (name) VALUES (?)
                    """, (tag_name,))
                    
                    cursor.execute("SELECT id FROM tags WHERE name = ?", (tag_name,))
                    tag_row = cursor.fetchone()
                    if not tag_row:
                        continue
                    
                    cursor.execute("""
                        INSERT OR IGNORE INTO account_tag_relations (account_email, tag_id)
                        VALUES (?, ?)
                    """, (email, tag_row[0]))
                
                conn.commit()
                return True
            except Exception as e:
                logger.error(f"添加标签失败: {e}")
                conn.rollback()
                return False
        
        return await self._run_in_thread(_sync_add)

    async def remove_tags_from_account(self, email: str, tags: list[str]) -> bool:
        """从账户移除指定标签"""
        
        def _sync_remove(conn: sqlite3.Connection) -> bool:
            try:
                cursor = conn.cursor()
                
                for tag_name in tags:
                    if not tag_name:
                        continue
                    
                    cursor.execute("""
                        DELETE FROM account_tag_relations
                        WHERE account_email = ?
                        AND tag_id = (SELECT id FROM tags WHERE name = ?)
                    """, (email, tag_name.strip()))
                
                conn.commit()
                return True
            except Exception as e:
                logger.error(f"移除标签失败: {e}")
                conn.rollback()
                return False
        
        return await self._run_in_thread(_sync_remove)

    async def get_all_tags_v2(self) -> list[str]:
        """获取所有唯一标签"""
        
        def _sync_get(conn: sqlite3.Connection) -> list[str]:
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM tags ORDER BY name")
            return [row[0] for row in cursor.fetchall()]
        
        return await self._run_in_thread(_sync_get)

    async def get_tag_statistics_v2(self) -> dict[str, Any]:
        """获取标签统计（使用 SQL 聚合）"""
        
        def _sync_get(conn: sqlite3.Connection) -> dict[str, Any]:
            cursor = conn.cursor()
            
            # 总账户数
            cursor.execute("SELECT COUNT(*) FROM accounts")
            total_accounts = cursor.fetchone()[0]
            
            # 有标签的账户数
            cursor.execute("""
                SELECT COUNT(DISTINCT account_email) FROM account_tag_relations
            """)
            tagged_accounts = cursor.fetchone()[0]
            
            # 各标签统计
            cursor.execute("""
                SELECT t.name, COUNT(atr.account_email) as count
                FROM tags t
                LEFT JOIN account_tag_relations atr ON t.id = atr.tag_id
                GROUP BY t.id, t.name
                ORDER BY count DESC, t.name
            """)
            
            tags_list = []
            for row in cursor.fetchall():
                percentage = round(row[1] / total_accounts * 100, 1) if total_accounts > 0 else 0
                tags_list.append({
                    "name": row[0],
                    "count": row[1],
                    "percentage": percentage,
                })
            
            return {
                "total_accounts": total_accounts,
                "tagged_accounts": tagged_accounts,
                "untagged_accounts": total_accounts - tagged_accounts,
                "tags": tags_list,
            }
        
        return await self._run_in_thread(_sync_get)

    async def get_random_account_by_tag_filter_v2(
        self,
        include_tag: str | None = None,
        exclude_tags: list[str] | None = None,
    ) -> dict[str, Any] | None:
        """
        使用 SQL 级过滤随机获取账户（高性能版本）
        """
        
        def _sync_get(conn: sqlite3.Connection) -> dict[str, Any] | None:
            cursor = conn.cursor()
            
            # 构建查询
            query = """
                SELECT a.email, a.password, a.client_id, a.refresh_token
                FROM accounts a
            """
            params: list[Any] = []
            
            # 必须有某个标签
            if include_tag:
                query += """
                    JOIN account_tag_relations atr ON a.email = atr.account_email
                    JOIN tags t ON atr.tag_id = t.id AND t.name = ?
                """
                params.append(include_tag)
            
            # 排除标签
            if exclude_tags:
                placeholders = ",".join(["?" for _ in exclude_tags])
                if include_tag:
                    query += f"""
                        WHERE a.email NOT IN (
                            SELECT atr2.account_email
                            FROM account_tag_relations atr2
                            JOIN tags t2 ON atr2.tag_id = t2.id
                            WHERE t2.name IN ({placeholders})
                        )
                    """
                else:
                    query += f"""
                        WHERE a.email NOT IN (
                            SELECT atr2.account_email
                            FROM account_tag_relations atr2
                            JOIN tags t2 ON atr2.tag_id = t2.id
                            WHERE t2.name IN ({placeholders})
                        )
                    """
                params.extend(exclude_tags)
            
            # 使用 COUNT + OFFSET 随机选择
            count_query = f"SELECT COUNT(*) FROM ({query}) sub"
            cursor.execute(count_query, params)
            total = cursor.fetchone()[0]
            
            if total == 0:
                return None
            
            offset = random.randint(0, total - 1)
            
            query += " LIMIT 1 OFFSET ?"
            params.append(offset)
            
            cursor.execute(query, params)
            row = cursor.fetchone()
            
            if not row:
                return None
            
            # 获取该账户的所有标签
            cursor.execute("""
                SELECT t.name FROM tags t
                JOIN account_tag_relations atr ON t.id = atr.tag_id
                WHERE atr.account_email = ?
            """, (row[0],))
            tags = [r[0] for r in cursor.fetchall()]
            
            return {
                "email": row[0],
                "password": row[1] or "",
                "client_id": row[2] or "",
                "refresh_token": row[3] or "",
                "tags": tags,
            }
        
        return await self._run_in_thread(_sync_get)

    async def delete_tag_globally_v2(self, tag_name: str) -> int:
        """全局删除标签"""
        
        def _sync_delete(conn: sqlite3.Connection) -> int:
            try:
                cursor = conn.cursor()
                
                # 获取受影响的账户数
                cursor.execute("""
                    SELECT COUNT(*) FROM account_tag_relations
                    WHERE tag_id = (SELECT id FROM tags WHERE name = ?)
                """, (tag_name,))
                affected = cursor.fetchone()[0]
                
                # 删除标签（级联删除关联）
                cursor.execute("DELETE FROM tags WHERE name = ?", (tag_name,))
                
                conn.commit()
                return affected
            except Exception as e:
                logger.error(f"全局删除标签失败: {e}")
                conn.rollback()
                return 0
        
        return await self._run_in_thread(_sync_delete)

    async def rename_tag_globally_v2(self, old_name: str, new_name: str) -> int:
        """全局重命名标签"""
        
        def _sync_rename(conn: sqlite3.Connection) -> int:
            try:
                cursor = conn.cursor()
                
                # 获取受影响的账户数
                cursor.execute("""
                    SELECT COUNT(*) FROM account_tag_relations
                    WHERE tag_id = (SELECT id FROM tags WHERE name = ?)
                """, (old_name,))
                affected = cursor.fetchone()[0]
                
                # 检查新名称是否已存在
                cursor.execute("SELECT id FROM tags WHERE name = ?", (new_name,))
                existing = cursor.fetchone()
                
                if existing:
                    # 合并到已存在的标签
                    cursor.execute("SELECT id FROM tags WHERE name = ?", (old_name,))
                    old_tag = cursor.fetchone()
                    if old_tag:
                        # 更新关联
                        cursor.execute("""
                            UPDATE OR IGNORE account_tag_relations
                            SET tag_id = ?
                            WHERE tag_id = ?
                        """, (existing[0], old_tag[0]))
                        # 删除旧标签
                        cursor.execute("DELETE FROM tags WHERE id = ?", (old_tag[0],))
                else:
                    # 直接重命名
                    cursor.execute("""
                        UPDATE tags SET name = ? WHERE name = ?
                    """, (new_name, old_name))
                
                conn.commit()
                return affected
            except Exception as e:
                logger.error(f"重命名标签失败: {e}")
                conn.rollback()
                return 0
        
        return await self._run_in_thread(_sync_rename)

    async def batch_update_tags_v2(
        self, emails: list[str], tags: list[str], action: str = "set"
    ) -> tuple[int, int]:
        """
        批量更新账户标签（使用关系表）。

        Args:
            emails: 邮箱列表
            tags: 标签列表
            action: "set" 替换, "add" 追加, "remove" 移除

        Returns:
            (更新成功数, 失败数)
        """

        def _sync_batch(conn: sqlite3.Connection) -> tuple[int, int]:
            cursor = conn.cursor()
            updated = 0
            failed = 0

            try:
                # 预先确保所有标签存在
                tag_ids: dict[str, int] = {}
                for tag_name in tags:
                    if not tag_name or not tag_name.strip():
                        continue
                    tag_name = tag_name.strip()
                    cursor.execute("INSERT OR IGNORE INTO tags (name) VALUES (?)", (tag_name,))
                    cursor.execute("SELECT id FROM tags WHERE name = ?", (tag_name,))
                    row = cursor.fetchone()
                    if row:
                        tag_ids[tag_name] = row[0]

                for email in emails:
                    try:
                        if action == "set":
                            # 删除现有关联
                            cursor.execute(
                                "DELETE FROM account_tag_relations WHERE account_email = ?",
                                (email,),
                            )
                            # 添加新关联
                            for tag_name, tag_id in tag_ids.items():
                                cursor.execute(
                                    """
                                    INSERT OR IGNORE INTO account_tag_relations (account_email, tag_id)
                                    VALUES (?, ?)
                                    """,
                                    (email, tag_id),
                                )
                        elif action == "add":
                            for tag_name, tag_id in tag_ids.items():
                                cursor.execute(
                                    """
                                    INSERT OR IGNORE INTO account_tag_relations (account_email, tag_id)
                                    VALUES (?, ?)
                                    """,
                                    (email, tag_id),
                                )
                        elif action == "remove":
                            for tag_name, tag_id in tag_ids.items():
                                cursor.execute(
                                    """
                                    DELETE FROM account_tag_relations
                                    WHERE account_email = ? AND tag_id = ?
                                    """,
                                    (email, tag_id),
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

        return await self._run_in_thread(_sync_batch)

    async def get_accounts_by_tag_filter_v2(
        self,
        tag: str | None = None,
        exclude_tags: list[str] | None = None,
        untagged_only: bool = False,
        search: str | None = None,
        page: int = 1,
        page_size: int = 10,
    ) -> tuple[list[dict[str, Any]], int]:
        """
        按标签条件筛选账户（优化版本，避免 N+1 查询）。

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
        from ..settings import get_settings
        _settings = get_settings()
        CLIENT_ID = _settings.client_id

        def _sync_get(conn: sqlite3.Connection) -> tuple[list[dict[str, Any]], int]:
            cursor = conn.cursor()

            # 构建基础查询
            base_query = """
                FROM accounts a
                WHERE a.deleted_at IS NULL
            """
            params: list[Any] = []

            # 搜索条件
            if search:
                base_query += " AND a.email LIKE ?"
                params.append(f"%{search}%")

            # 标签过滤条件
            if tag:
                base_query += """
                    AND EXISTS (
                        SELECT 1 FROM account_tag_relations atr
                        JOIN tags t ON atr.tag_id = t.id
                        WHERE atr.account_email = a.email AND t.name = ?
                    )
                """
                params.append(tag)

            if exclude_tags:
                placeholders = ",".join(["?" for _ in exclude_tags])
                base_query += f"""
                    AND NOT EXISTS (
                        SELECT 1 FROM account_tag_relations atr
                        JOIN tags t ON atr.tag_id = t.id
                        WHERE atr.account_email = a.email AND t.name IN ({placeholders})
                    )
                """
                params.extend(exclude_tags)

            if untagged_only:
                base_query += """
                    AND NOT EXISTS (
                        SELECT 1 FROM account_tag_relations atr
                        WHERE atr.account_email = a.email
                    )
                """

            # 获取总数
            count_sql = f"SELECT COUNT(*) {base_query}"
            cursor.execute(count_sql, params)
            total = cursor.fetchone()[0]

            # 分页查询账户（使用 GROUP_CONCAT 获取标签，避免 N+1）
            offset = (page - 1) * page_size
            query_sql = f"""
                SELECT a.email, a.password, a.client_id, a.refresh_token,
                       a.is_used, a.last_used_at,
                       (
                           SELECT GROUP_CONCAT(t.name, ',')
                           FROM account_tag_relations atr
                           JOIN tags t ON atr.tag_id = t.id
                           WHERE atr.account_email = a.email
                       ) as tags
                {base_query}
                ORDER BY a.email
                LIMIT ? OFFSET ?
            """
            query_params = params + [page_size, offset]
            cursor.execute(query_sql, query_params)

            result = []
            for row in cursor.fetchall():
                tags_str = row[6]  # tags 列
                account_tags = tags_str.split(',') if tags_str else []

                result.append({
                    "email": row[0],
                    "password": row[1] or "",
                    "client_id": row[2] or CLIENT_ID,
                    "refresh_token": row[3] or "",
                    "is_used": bool(row[4]) if row[4] is not None else False,
                    "last_used_at": row[5],
                    "tags": account_tags,
                })

            return result, total

        return await self._run_in_thread(_sync_get)

    async def cleanup_orphan_tags(self) -> int:
        """清理没有关联任何账户的孤立标签"""
        
        def _sync_cleanup(conn: sqlite3.Connection) -> int:
            try:
                cursor = conn.cursor()
                cursor.execute("""
                    DELETE FROM tags
                    WHERE id NOT IN (
                        SELECT DISTINCT tag_id FROM account_tag_relations
                    )
                """)
                deleted = cursor.rowcount
                conn.commit()
                logger.info(f"清理了 {deleted} 个孤立标签")
                return deleted
            except Exception as e:
                logger.error(f"清理孤立标签失败: {e}")
                conn.rollback()
                return 0

        return await self._run_in_thread(_sync_cleanup)
