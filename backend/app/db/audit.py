#!/usr/bin/env python3
"""
Audit and rate limiting module.

Handles login audit logging and rate limiting related database operations:
- Login attempt recording
- Failure counting
- Account lockout management
- General audit event storage
"""

import json
import logging
import sqlite3
from datetime import datetime

logger = logging.getLogger(__name__)

from .base import RunInThreadMixin


class AuditMixin(RunInThreadMixin):
    """Mixin providing audit and rate limiting database operations."""

    async def store_audit_event(self, event: dict) -> bool:
        """
        存储审计事件到 audit_events 表。
        
        Args:
            event: 审计事件字典，包含以下字段：
                - event_type: 事件类型
                - timestamp: 时间戳
                - user_id: 用户ID（可选）
                - ip_address: IP地址（可选）
                - user_agent: 用户代理（可选）
                - resource: 资源（可选）
                - action: 操作（可选）
                - details: 详情字典（可选）
                - success: 是否成功
                - error_message: 错误消息（可选）
        
        Returns:
            是否存储成功
        """

        def _sync_store(conn: sqlite3.Connection) -> bool:
            try:
                cursor = conn.cursor()
                
                # 处理 timestamp - 可能是 datetime 对象或字符串
                timestamp = event.get("timestamp")
                if isinstance(timestamp, datetime):
                    timestamp = timestamp.isoformat()
                
                # 处理 event_type - 可能是枚举或字符串
                event_type = event.get("event_type")
                if hasattr(event_type, "value"):
                    event_type = event_type.value
                
                cursor.execute("""
                    INSERT INTO audit_events 
                    (event_type, timestamp, user_id, ip_address, user_agent, 
                     resource, action, details, success, error_message)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    event_type,
                    timestamp,
                    event.get("user_id"),
                    event.get("ip_address"),
                    event.get("user_agent"),
                    event.get("resource"),
                    event.get("action"),
                    json.dumps(event.get("details")) if event.get("details") else None,
                    1 if event.get("success", True) else 0,
                    event.get("error_message"),
                ))
                conn.commit()
                return True
            except Exception as e:
                logger.error(f"存储审计事件失败: {e}")
                return False

        return await self._run_in_thread(_sync_store)

    async def get_audit_events(
        self,
        event_type: str | None = None,
        user_id: str | None = None,
        ip_address: str | None = None,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[dict]:
        """
        查询审计事件。
        
        Args:
            event_type: 事件类型过滤
            user_id: 用户ID过滤
            ip_address: IP地址过滤
            start_time: 开始时间
            end_time: 结束时间
            limit: 返回数量限制
            offset: 偏移量
            
        Returns:
            审计事件列表
        """

        def _sync_get(conn: sqlite3.Connection) -> list[dict]:
            cursor = conn.cursor()
            
            query = "SELECT * FROM audit_events WHERE 1=1"
            params: list = []
            
            if event_type:
                query += " AND event_type = ?"
                params.append(event_type)
            if user_id:
                query += " AND user_id = ?"
                params.append(user_id)
            if ip_address:
                query += " AND ip_address = ?"
                params.append(ip_address)
            if start_time:
                query += " AND timestamp >= ?"
                params.append(start_time.isoformat())
            if end_time:
                query += " AND timestamp <= ?"
                params.append(end_time.isoformat())
            
            query += " ORDER BY id DESC LIMIT ? OFFSET ?"
            params.extend([limit, offset])
            
            cursor.execute(query, params)
            rows = cursor.fetchall()
            
            events = []
            for row in rows:
                event = dict(row)
                if event.get("details"):
                    try:
                        event["details"] = json.loads(event["details"])
                    except json.JSONDecodeError as e:
                        logger.warning(f"解析审计事件详情 JSON 失败 (id={event.get('id', 'unknown')}): {e}")
                event["success"] = bool(event.get("success", 1))
                events.append(event)
            
            return events

        return await self._run_in_thread(_sync_get)

    async def cleanup_old_audit_events(self, days: int = 90) -> int:
        """
        清理旧的审计事件。
        
        Args:
            days: 保留天数
            
        Returns:
            删除的事件数量
        """
        days = max(1, min(int(days), 365))

        def _sync_cleanup(conn: sqlite3.Connection) -> int:
            try:
                cursor = conn.cursor()
                from datetime import timedelta
                threshold = (datetime.utcnow() - timedelta(days=days)).isoformat()
                cursor.execute(
                    "DELETE FROM audit_events WHERE timestamp < ?",
                    (threshold,),
                )
                deleted = cursor.rowcount
                conn.commit()
                return deleted
            except Exception as e:
                logger.error(f"清理旧审计事件失败: {e}")
                return 0

        return await self._run_in_thread(_sync_cleanup)

    async def record_login_attempt(
        self, ip: str, username: str, success: bool, reason: str = ""
    ) -> None:
        """Record a login attempt."""

        def _sync_record(conn: sqlite3.Connection) -> None:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO admin_login_attempts (ip, username, success, reason)
                VALUES (?, ?, ?, ?)
                """,
                (ip, username, 1 if success else 0, reason),
            )
            conn.commit()

        await self._run_in_thread(_sync_record)

    async def count_recent_failures(
        self, ip: str, username: str, window_seconds: int
    ) -> int:
        """Count recent login failures within a time window."""

        def _sync_count(conn: sqlite3.Connection) -> int:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT COUNT(*) FROM admin_login_attempts
                WHERE ip = ? AND username = ? AND success = 0
                  AND created_at > datetime('now', ?)
                  AND id > COALESCE(
                    (
                      SELECT MAX(id) FROM admin_login_attempts
                      WHERE ip = ? AND username = ? AND success = 1
                    ),
                    0
                  )
                """,
                (ip, username, f"-{window_seconds} seconds", ip, username),
            )
            row = cursor.fetchone()
            return row[0] if row else 0

        return await self._run_in_thread(_sync_count)

    async def set_lockout(
        self, ip: str, username: str, lockout_until: datetime
    ) -> None:
        """Set account lockout."""

        def _sync_set(conn: sqlite3.Connection) -> None:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO admin_lockouts (ip, username, lockout_until)
                VALUES (?, ?, ?)
                ON CONFLICT(ip, username) DO UPDATE SET lockout_until=excluded.lockout_until
                """,
                (ip, username, lockout_until.isoformat()),
            )
            conn.commit()

        await self._run_in_thread(_sync_set)

    async def get_lockout(self, ip: str, username: str) -> datetime | None:
        """
        Get lockout expiration time.
        
        Automatically clears expired lockouts.
        """

        def _sync_get(conn: sqlite3.Connection) -> datetime | None:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT lockout_until FROM admin_lockouts
                WHERE ip = ? AND username = ?
                """,
                (ip, username),
            )
            row = cursor.fetchone()
            if not row:
                return None
            lockout_until = datetime.fromisoformat(row["lockout_until"])
            if lockout_until < datetime.utcnow():
                cursor.execute(
                    "DELETE FROM admin_lockouts WHERE ip = ? AND username = ?",
                    (ip, username),
                )
                conn.commit()
                return None
            return lockout_until

        return await self._run_in_thread(_sync_get)

    async def clear_lockout(self, ip: str, username: str) -> None:
        """Clear account lockout."""

        def _sync_clear(conn: sqlite3.Connection) -> None:
            cursor = conn.cursor()
            cursor.execute(
                "DELETE FROM admin_lockouts WHERE ip = ? AND username = ?",
                (ip, username),
            )
            conn.commit()

        await self._run_in_thread(_sync_clear)

    async def get_login_audit_stats(self) -> dict:
        """Get login audit statistics."""

        def _sync_stats(conn: sqlite3.Connection) -> dict:
            cursor = conn.cursor()

            # Total attempts
            cursor.execute("SELECT COUNT(*) FROM admin_login_attempts")
            total = cursor.fetchone()[0]

            # Successful logins
            cursor.execute("SELECT COUNT(*) FROM admin_login_attempts WHERE success = 1")
            successful = cursor.fetchone()[0]

            # Failed logins
            cursor.execute("SELECT COUNT(*) FROM admin_login_attempts WHERE success = 0")
            failed = cursor.fetchone()[0]

            # Active lockouts
            cursor.execute(
                """
                SELECT COUNT(*) FROM admin_lockouts 
                WHERE lockout_until > datetime('now')
                """
            )
            active_lockouts = cursor.fetchone()[0]

            # Recent failures (last 24 hours)
            cursor.execute(
                """
                SELECT COUNT(*) FROM admin_login_attempts 
                WHERE success = 0 AND created_at > datetime('now', '-1 day')
                """
            )
            recent_failures = cursor.fetchone()[0]

            return {
                "total_attempts": total,
                "successful_logins": successful,
                "failed_logins": failed,
                "active_lockouts": active_lockouts,
                "recent_failures_24h": recent_failures,
            }

        return await self._run_in_thread(_sync_stats)

    async def cleanup_old_audit_logs(self, days: int = 90) -> int:
        """Clean up old audit logs."""
        # 白名单校验：限制 days 参数范围，防止异常输入
        days = max(1, min(int(days), 365))

        def _sync_cleanup(conn: sqlite3.Connection) -> int:
            try:
                cursor = conn.cursor()
                # 使用参数化查询：先计算阈值时间，避免 f-string 拼接
                from datetime import timedelta
                threshold = (datetime.utcnow() - timedelta(days=days)).isoformat()
                cursor.execute(
                    "DELETE FROM admin_login_attempts WHERE created_at < ?",
                    (threshold,),
                )
                deleted = cursor.rowcount
                conn.commit()
                return deleted
            except Exception as e:
                logger.error(f"清理旧审计日志失败: {e}")
                return 0

        return await self._run_in_thread(_sync_cleanup)
