#!/usr/bin/env python3
"""
SQLite数据库管理模块
用于管理邮件和标签数据
"""

import sqlite3
import json
import logging
import re
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
from datetime import datetime
from typing import Callable, Dict, List, Optional, Tuple, TypeVar
import asyncio

from pathlib import Path

from .config import CLIENT_ID
from .migrations import apply_migrations
from .security import encrypt_if_needed, decrypt_if_needed
from .settings import get_settings

settings = get_settings()
PROJECT_ROOT = Path(__file__).resolve().parents[2]

logger = logging.getLogger(__name__)

GUID_PATTERN = re.compile(r"^[0-9a-fA-F]{8}-(?:[0-9a-fA-F]{4}-){3}[0-9a-fA-F]{12}$")
T = TypeVar("T")

def looks_like_guid(value: str) -> bool:
    if not value:
        return False
    return bool(GUID_PATTERN.match(value.strip()))

class DatabaseManager:
    """数据库管理器"""
    
    def __init__(self, db_path: str = settings.database_path):
        resolved = Path(db_path)
        if not resolved.is_absolute():
            resolved = PROJECT_ROOT / resolved
        resolved.parent.mkdir(parents=True, exist_ok=True)
        self.db_path = str(resolved)
        # 专用线程池执行器，用于承载所有同步 SQLite 操作
        self._executor: Optional[ThreadPoolExecutor] = None
        self._executor_loop: Optional[asyncio.AbstractEventLoop] = None
        self.init_database()

    def _create_connection(self) -> sqlite3.Connection:
        """创建新的 SQLite 连接并启用行工厂"""
        conn = sqlite3.connect(self.db_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn

    def get_connection(self) -> sqlite3.Connection:
        """兼容旧代码的同步连接获取接口，调用方需负责关闭"""
        return self._create_connection()

    def _get_executor(self) -> ThreadPoolExecutor:
        """获取或创建数据库专用线程池执行器。

        为了兼容测试环境中可能存在的多个事件循环，
        当检测到事件循环变化时，会创建新的执行器并关闭旧的。
        """
        loop = asyncio.get_running_loop()
        if self._executor is None or self._executor_loop is not loop:
            # 关闭旧执行器，避免线程泄露
            if self._executor is not None:
                self._executor.shutdown(wait=False)
            self._executor = ThreadPoolExecutor(
                max_workers=4,
                thread_name_prefix="db-worker",
            )
            self._executor_loop = loop
        return self._executor

    async def _run_in_thread(self, handler: Callable[[sqlite3.Connection], T]) -> T:
        """在后台线程池中运行数据库操作并确保连接被释放"""

        def _runner() -> T:
            with closing(self._create_connection()) as conn:
                return handler(conn)

        loop = asyncio.get_running_loop()
        executor = self._get_executor()
        return await loop.run_in_executor(executor, _runner)
    
    def init_database(self):
        """初始化数据库表"""
        with closing(self._create_connection()) as conn:
            cursor = conn.cursor()
            
            # 创建账户表
            cursor.execute('''
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
            ''')
            
            # 创建账户标签表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS account_tags (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    email TEXT NOT NULL,
                    tags TEXT NOT NULL,  -- JSON格式存储标签数组
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # 创建邮件缓存表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS email_cache (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    email TEXT NOT NULL,
                    message_id TEXT NOT NULL,
                    subject TEXT,
                    sender TEXT,
                    received_date TEXT,
                    body_preview TEXT,
                    body_content TEXT,
                    body_type TEXT DEFAULT 'text',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(email, message_id)
                )
            ''')
            
            # 创建系统配置表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS system_config (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # 创建索引
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_accounts_email ON accounts(email)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_account_tags_email ON account_tags(email)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_email_cache_email ON email_cache(email)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_email_cache_message_id ON email_cache(message_id)')
            
            conn.commit()
            apply_migrations(conn)
            logger.info("数据库初始化完成")
    
    async def get_account_tags(self, email: str) -> List[str]:
        """获取账户标签"""
        def _sync_get(conn):
            cursor = conn.cursor()
            cursor.execute('SELECT tags FROM account_tags WHERE email = ?', (email,))
            row = cursor.fetchone()
            if row:
                try:
                    return json.loads(row['tags'])
                except json.JSONDecodeError:
                    return []
            return []
        
        return await self._run_in_thread(_sync_get)
    
    async def set_account_tags(self, email: str, tags: List[str]) -> bool:
        """设置账户标签"""
        def _sync_set(conn):
            try:
                cursor = conn.cursor()
                tags_json = json.dumps(tags, ensure_ascii=False)
                
                # 先检查记录是否存在
                cursor.execute('SELECT id FROM account_tags WHERE email = ?', (email,))
                existing_record = cursor.fetchone()
                
                if existing_record:
                    # 更新现有记录
                    cursor.execute('''
                        UPDATE account_tags 
                        SET tags = ?, updated_at = CURRENT_TIMESTAMP 
                        WHERE email = ?
                    ''', (tags_json, email))
                    logger.info(f"更新账户 {email} 的标签: {tags}")
                else:
                    # 插入新记录
                    cursor.execute('''
                        INSERT INTO account_tags (email, tags, created_at, updated_at) 
                        VALUES (?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                    ''', (email, tags_json))
                    logger.info(f"为账户 {email} 创建新标签: {tags}")
                
                conn.commit()
                logger.info(f"成功保存账户 {email} 的标签")
                return True
            except Exception as e:
                logger.error(f"设置账户标签失败: {e}")
                conn.rollback()
                return False
        
        return await self._run_in_thread(_sync_set)
    
    async def get_all_tags(self) -> List[str]:
        """获取所有标签"""
        def _sync_get(conn):
            cursor = conn.cursor()
            cursor.execute('SELECT tags FROM account_tags')
            rows = cursor.fetchall()
            
            all_tags = set()
            for row in rows:
                try:
                    tags = json.loads(row['tags'])
                    all_tags.update(tags)
                except json.JSONDecodeError:
                    continue
            
            return sorted(list(all_tags))
        
        return await self._run_in_thread(_sync_get)
    
    async def get_accounts_with_tags(self) -> Dict[str, List[str]]:
        """获取所有账户及其标签"""
        def _sync_get(conn):
            cursor = conn.cursor()
            cursor.execute('SELECT email, tags FROM account_tags')
            rows = cursor.fetchall()
            
            result = {}
            for row in rows:
                try:
                    tags = json.loads(row['tags'])
                    result[row['email']] = tags
                except json.JSONDecodeError:
                    result[row['email']] = []
            
            return result
        
        return await self._run_in_thread(_sync_get)
    
    async def cache_email(self, email: str, message_id: str, email_data: Dict) -> bool:
        """缓存邮件数据并进行容量控制

        - 每个账户最多保留最近 100 封缓存邮件
        - 旧邮件按创建时间(created_at)从旧到新淘汰
        """

        def _sync_cache(conn):
            try:
                cursor = conn.cursor()

                # 提取邮件信息
                subject = email_data.get('subject', '')
                sender_info = email_data.get('sender', {}).get('emailAddress', {})
                sender = f"{sender_info.get('name', '')} <{sender_info.get('address', '')}>"
                received_date = email_data.get('receivedDateTime', '')
                body_preview = email_data.get('bodyPreview', '')
                body_info = email_data.get('body', {})
                body_content = body_info.get('content', '')
                body_type = body_info.get('contentType', 'text')

                cursor.execute('''
                    INSERT OR REPLACE INTO email_cache
                    (email, message_id, subject, sender, received_date, body_preview, body_content, body_type)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (email, message_id, subject, sender, received_date, body_preview, body_content, body_type))

                # 容量控制: 每个账户最多保留最近 100 封缓存邮件
                cursor.execute(
                    '''
                    DELETE FROM email_cache
                    WHERE email = ?
                      AND id NOT IN (
                          SELECT id FROM email_cache
                          WHERE email = ?
                          ORDER BY created_at DESC
                          LIMIT 100
                      )
                    ''',
                    (email, email),
                )

                conn.commit()
                return True
            except Exception as e:
                logger.error(f"缓存邮件失败: {e}")
                return False

        return await self._run_in_thread(_sync_cache)

    async def get_cached_email(self, email: str, message_id: str) -> Optional[Dict]:
        """获取缓存的邮件数据"""
        def _sync_get(conn):
            cursor = conn.cursor()
            cursor.execute('''
                SELECT * FROM email_cache 
                WHERE email = ? AND message_id = ?
            ''', (email, message_id))
            row = cursor.fetchone()
            
            if row:
                return {
                    'id': row['message_id'],
                    'subject': row['subject'],
                    'sender': {'emailAddress': {'name': row['sender'].split(' <')[0] if ' <' in row['sender'] else row['sender'],
                                               'address': row['sender'].split('<')[1].rstrip('>') if '<' in row['sender'] else row['sender']}},
                    'receivedDateTime': row['received_date'],
                    'bodyPreview': row['body_preview'],
                    'body': {'content': row['body_content'], 'contentType': row['body_type']}
                }
            return None
        
        return await self._run_in_thread(_sync_get)
    
    async def get_system_config(self, key: str, default_value: str = None) -> Optional[str]:
        """获取系统配置"""
        def _sync_get(conn):
            cursor = conn.cursor()
            cursor.execute('SELECT value FROM system_config WHERE key = ?', (key,))
            row = cursor.fetchone()
            return row['value'] if row else default_value
        
        return await self._run_in_thread(_sync_get)
    
    async def set_system_config(self, key: str, value: str) -> bool:
        """设置系统配置"""
        def _sync_set(conn):
            try:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT OR REPLACE INTO system_config (key, value, updated_at)
                    VALUES (?, ?, CURRENT_TIMESTAMP)
                ''', (key, value))
                conn.commit()
                return True
            except Exception as e:
                logger.error(f"设置系统配置失败: {e}")
                return False
        
        return await self._run_in_thread(_sync_set)

    async def upsert_system_metric(self, key: str, value) -> bool:
        """写入或更新系统指标"""
        def _sync_upsert(conn):
            try:
                cursor = conn.cursor()

                if isinstance(value, (dict, list)):
                    payload = json.dumps(value, ensure_ascii=False)
                else:
                    payload = str(value)

                cursor.execute(
                    """
                    INSERT INTO system_metrics (key, value, updated_at)
                    VALUES (?, ?, CURRENT_TIMESTAMP)
                    ON CONFLICT(key) DO UPDATE SET
                        value=excluded.value,
                        updated_at=CURRENT_TIMESTAMP
                    """,
                    (key, payload),
                )
                conn.commit()
                return True
            except Exception as e:
                logger.error(f"写入系统指标失败: {e}")
                return False

        return await self._run_in_thread(_sync_upsert)

    async def get_all_system_metrics(self) -> Dict[str, str]:
        """读取所有系统指标"""
        def _sync_get(conn):
            cursor = conn.cursor()
            cursor.execute("SELECT key, value, updated_at FROM system_metrics")
            rows = cursor.fetchall()
            return {
                row["key"]: {
                    "value": row["value"],
                    "updated_at": row["updated_at"],
                }
                for row in rows
            }
        
        return await self._run_in_thread(_sync_get)

    async def get_email_cache_stats(self) -> Dict[str, int]:
        """返回 email_cache 的聚合统计"""
        def _sync_stats(conn):
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT COUNT(*) AS total_messages, COUNT(DISTINCT email) AS cached_accounts
                FROM email_cache
                """
            )
            row = cursor.fetchone()
            return {
                "total_messages": row["total_messages"] if row else 0,
                "cached_accounts": row["cached_accounts"] if row else 0,
            }

        return await self._run_in_thread(_sync_stats)

    async def reset_email_cache(self) -> None:
        """清空邮件缓存"""
        def _sync_reset(conn):
            cursor = conn.cursor()
            cursor.execute("DELETE FROM email_cache")
            conn.commit()

        await self._run_in_thread(_sync_reset)
    
    async def cleanup_old_emails(self, days: int = 30) -> int:
        """清理旧的邮件缓存"""
        def _sync_cleanup(conn):
            try:
                cursor = conn.cursor()
                cursor.execute('''
                    DELETE FROM email_cache 
                    WHERE created_at < datetime('now', '-{} days')
                '''.format(days))
                deleted_count = cursor.rowcount
                conn.commit()
                return deleted_count
            except Exception as e:
                logger.error(f"清理旧邮件失败: {e}")
                return 0
        
        return await self._run_in_thread(_sync_cleanup)
    
    async def get_all_accounts(self) -> Dict[str, Dict[str, str]]:
        """获取所有账户"""
        def _sync_get(conn):
            cursor = conn.cursor()
            cursor.execute(
                '''
                SELECT email, password, client_id, refresh_token, is_used, last_used_at
                FROM accounts
                '''
            )
            rows = cursor.fetchall()
            
            result = {}
            for row in rows:
                result[row['email']] = {
                    'password': row['password'] or '',
                    'client_id': row['client_id'] or CLIENT_ID,
                    'refresh_token': row['refresh_token'],
                    'is_used': bool(row['is_used']) if row['is_used'] is not None else False,
                    'last_used_at': row['last_used_at'],
            }
            return result
        
        return await self._run_in_thread(_sync_get)
    
    async def get_first_unused_account_email(self) -> Optional[str]:
        """获取一个未使用的账户邮箱（按创建时间排序）

        如果不存在未使用的账户，则返回 None。
        """

        def _sync_get(conn):
            cursor = conn.cursor()
            cursor.execute(
                '''
                SELECT email
                FROM accounts
                WHERE is_used = 0
                ORDER BY created_at ASC
                LIMIT 1
                '''
            )
            row = cursor.fetchone()
            return row["email"] if row else None

        return await self._run_in_thread(_sync_get)
    
    async def mark_account_used(self, email: str) -> bool:
        """将账户标记为已使用，并记录最后使用时间"""

        def _sync_mark(conn):
            try:
                cursor = conn.cursor()
                cursor.execute(
                    '''
                    UPDATE accounts
                    SET is_used = 1,
                        last_used_at = CURRENT_TIMESTAMP,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE email = ?
                    ''',
                    (email,),
                )
                conn.commit()
                return cursor.rowcount > 0
            except Exception as e:
                logger.error(f"标记账户为已使用失败: {e}")
                return False

        return await self._run_in_thread(_sync_mark)
    
    async def replace_all_accounts(self, accounts: Dict[str, Dict[str, str]]) -> bool:
        """用提供的数据全集替换账户表"""
        def _sync_replace(conn):
            cursor = conn.cursor()
            try:
                cursor.execute('DELETE FROM accounts')
                entries = []
                for email, info in accounts.items():
                    entries.append(
                        (
                            email,
                            encrypt_if_needed(info.get('password', '')),
                            info.get('client_id', CLIENT_ID),
                            encrypt_if_needed(info.get('refresh_token', '')),
                        )
                    )

                if entries:
                    cursor.executemany(
                        'INSERT INTO accounts (email, password, client_id, refresh_token) VALUES (?, ?, ?, ?)',
                        entries
                    )
                conn.commit()
                return True
            except Exception as e:
                logger.error(f"替换账户数据失败: {e}")
                conn.rollback()
                return False
        
        return await self._run_in_thread(_sync_replace)
    
    async def add_account(self, email: str, password: str = '', client_id: str = '', refresh_token: str = '') -> bool:
        """添加账户"""
        def _sync_add(conn):
            try:
                cursor = conn.cursor()
                cursor.execute(
                    '''
                    INSERT INTO accounts (email, password, client_id, refresh_token)
                    VALUES (?, ?, ?, ?)
                ''',
                    (
                        email,
                        encrypt_if_needed(password or ''),
                        client_id or CLIENT_ID,
                        encrypt_if_needed(refresh_token or ''),
                    ),
                )
                conn.commit()
                return True
            except sqlite3.IntegrityError:
                # 账户已存在
                return False
            except Exception as e:
                logger.error(f"添加账户失败: {e}")
                return False
        
        return await self._run_in_thread(_sync_add)
    
    async def update_account(self, email: str, password: str = None, client_id: str = None, refresh_token: str = None) -> bool:
        """更新账户"""
        def _sync_update(conn):
            try:
                cursor = conn.cursor()
                
                # 构建更新语句
                updates = []
                params = []
                
                if password is not None:
                    updates.append('password = ?')
                    params.append(encrypt_if_needed(password or ''))
                
                if client_id is not None:
                    updates.append('client_id = ?')
                    params.append(client_id)
                
                if refresh_token is not None:
                    updates.append('refresh_token = ?')
                    params.append(encrypt_if_needed(refresh_token or ''))
                
                if not updates:
                    return True  # 没有更新内容
                
                updates.append('updated_at = CURRENT_TIMESTAMP')
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
        """删除账户"""
        def _sync_delete(conn):
            try:
                cursor = conn.cursor()
                
                # 删除账户
                cursor.execute('DELETE FROM accounts WHERE email = ?', (email,))
                account_deleted = cursor.rowcount > 0
                
                # 同时删除相关的标签
                cursor.execute('DELETE FROM account_tags WHERE email = ?', (email,))
                
                # 删除相关的邮件缓存
                cursor.execute('DELETE FROM email_cache WHERE email = ?', (email,))
                
                conn.commit()
                return account_deleted
            except Exception as e:
                logger.error(f"删除账户失败: {e}")
                return False
        
        return await self._run_in_thread(_sync_delete)
    
    async def account_exists(self, email: str) -> bool:
        """检查账户是否存在"""
        def _sync_check(conn):
            cursor = conn.cursor()
            cursor.execute('SELECT 1 FROM accounts WHERE email = ?', (email,))
            return cursor.fetchone() is not None
        
        return await self._run_in_thread(_sync_check)
    
    async def get_account(self, email: str) -> Optional[Dict[str, str]]:
        """获取单个账户信息"""
        def _sync_get(conn):
            cursor = conn.cursor()
            cursor.execute(
                '''
                SELECT password, client_id, refresh_token, is_used, last_used_at
                FROM accounts
                WHERE email = ?
                ''',
                (email,),
            )
            row = cursor.fetchone()
            if row:
                return {
                    'password': decrypt_if_needed(row['password']) if row['password'] else '',
                    'client_id': row['client_id'] or CLIENT_ID,
                    'refresh_token': decrypt_if_needed(row['refresh_token']) if row['refresh_token'] else '',
                    'is_used': bool(row['is_used']) if row['is_used'] is not None else False,
                    'last_used_at': row['last_used_at'],
                }
            return None
        
        return await self._run_in_thread(_sync_get)
    
    async def migrate_from_config_file(self, config_file_path: str = 'config.txt') -> Tuple[int, int]:
        """从config.txt迁移数据到数据库"""
        def _sync_migrate(conn):
            try:
                import os
                if not os.path.exists(config_file_path):
                    return 0, 0

                cursor = conn.cursor()
                
                added_count = 0
                error_count = 0
                
                with open(config_file_path, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                
                for line in lines:
                    line = line.strip()
                    if line.startswith('#') or not line:
                        continue

                    try:
                        parts = line.split('----')
                        if len(parts) >= 4:
                            # 标准格式：邮箱----密码----refresh_token----client_id
                            email = parts[0].strip()
                            password = parts[1].strip()
                            refresh_token = parts[2].strip()
                            client_id = parts[3].strip() or CLIENT_ID

                            cursor.execute('SELECT 1 FROM accounts WHERE email = ?', (email,))
                            if not cursor.fetchone():
                                cursor.execute('''
                                    INSERT INTO accounts (email, password, client_id, refresh_token)
                                    VALUES (?, ?, ?, ?)
                                ''', (
                                    email,
                                    encrypt_if_needed(password or ''),
                                    client_id,
                                    encrypt_if_needed(refresh_token or ''),
                                ))
                                added_count += 1
                        elif len(parts) == 2:
                            # 简化格式：邮箱----refresh_token
                            email = parts[0].strip()
                            refresh_token = parts[1].strip()
                            cursor.execute('SELECT 1 FROM accounts WHERE email = ?', (email,))
                            if not cursor.fetchone():
                                cursor.execute('''
                                    INSERT INTO accounts (email, password, client_id, refresh_token)
                                    VALUES (?, ?, ?, ?)
                                ''', (
                                    email,
                                    '',
                                    CLIENT_ID,
                                    encrypt_if_needed(refresh_token or ''),
                                ))
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
    
    def close(self):
        """关闭与数据库管理器相关的资源。

        目前主要用于关闭内部线程池执行器，兼容旧接口行为。
        实际的 SQLite 连接在每次调用中已经按粒度自动关闭。
        """
        if self._executor is not None:
            self._executor.shutdown(wait=True)
            self._executor = None
            self._executor_loop = None
        return None

# 全局数据库管理器实例
db_manager = DatabaseManager()
