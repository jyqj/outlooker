#!/usr/bin/env python3
"""
Audit logging system for tracking security-relevant events.
"""

import logging
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel

from ..auth.security import mask_email

logger = logging.getLogger(__name__)


class AuditEventType(str, Enum):
    """审计事件类型"""
    # 认证事件
    LOGIN_SUCCESS = "login_success"
    LOGIN_FAILED = "login_failed"
    LOGOUT = "logout"
    TOKEN_REFRESH = "token_refresh"
    TOKEN_REVOKED = "token_revoked"
    
    # 账户管理
    ACCOUNT_CREATED = "account_created"
    ACCOUNT_UPDATED = "account_updated"
    ACCOUNT_DELETED = "account_deleted"
    ACCOUNT_RESTORED = "account_restored"
    ACCOUNT_IMPORT = "account_import"
    ACCOUNT_EXPORT = "account_export"
    
    # 标签管理
    TAG_CREATED = "tag_created"
    TAG_DELETED = "tag_deleted"
    TAG_RENAMED = "tag_renamed"
    BATCH_TAG_UPDATE = "batch_tag_update"
    
    # 系统配置
    CONFIG_CHANGED = "config_changed"
    
    # API 访问
    PUBLIC_API_ACCESS = "public_api_access"
    RATE_LIMIT_EXCEEDED = "rate_limit_exceeded"


class AuditEvent(BaseModel):
    """审计事件模型"""
    event_type: AuditEventType
    timestamp: datetime
    user_id: str | None = None  # admin user id
    ip_address: str | None = None
    user_agent: str | None = None
    resource: str | None = None  # affected resource
    action: str | None = None  # specific action
    details: dict[str, Any] | None = None
    success: bool = True
    error_message: str | None = None


class AuditLogger:
    """审计日志记录器"""
    
    def __init__(self, db_manager=None):
        self._db_manager = db_manager
        self._logger = logging.getLogger("audit")
    
    async def log(
        self,
        event_type: AuditEventType,
        *,
        user_id: str | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
        resource: str | None = None,
        action: str | None = None,
        details: dict[str, Any] | None = None,
        success: bool = True,
        error_message: str | None = None,
    ) -> None:
        """记录审计事件"""
        event = AuditEvent(
            event_type=event_type,
            timestamp=datetime.now(timezone.utc),
            user_id=user_id,
            ip_address=ip_address,
            user_agent=user_agent,
            resource=resource,
            action=action,
            details=details,
            success=success,
            error_message=error_message,
        )
        
        # 记录到日志
        log_level = logging.INFO if success else logging.WARNING
        self._logger.log(
            log_level,
            "[AUDIT] %s | user=%s ip=%s resource=%s success=%s",
            event_type.value,
            user_id or "anonymous",
            ip_address or "unknown",
            resource or "-",
            success,
        )
        
        # 存储到数据库
        if self._db_manager:
            try:
                await self._db_manager.store_audit_event(event.model_dump())
            except Exception as e:
                logger.error(f"存储审计事件失败: {e}")
    
    async def log_login(
        self,
        ip_address: str,
        username: str,
        success: bool,
        reason: str | None = None,
        user_agent: str | None = None,
    ) -> None:
        """记录登录事件"""
        await self.log(
            AuditEventType.LOGIN_SUCCESS if success else AuditEventType.LOGIN_FAILED,
            user_id=username if success else None,
            ip_address=ip_address,
            user_agent=user_agent,
            resource="auth",
            action="login",
            details={"username": username},
            success=success,
            error_message=reason if not success else None,
        )
    
    async def log_api_access(
        self,
        ip_address: str,
        endpoint: str,
        method: str,
        token_prefix: str | None = None,
        success: bool = True,
        error_message: str | None = None,
    ) -> None:
        """记录 API 访问"""
        await self.log(
            AuditEventType.PUBLIC_API_ACCESS,
            ip_address=ip_address,
            resource=endpoint,
            action=method,
            details={"token_prefix": token_prefix} if token_prefix else None,
            success=success,
            error_message=error_message,
        )
    
    async def log_account_operation(
        self,
        event_type: AuditEventType,
        user_id: str,
        emails: list[str],
        ip_address: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        """记录账户操作（邮件地址脱敏）"""
        # 脱敏邮件地址
        masked_emails = [mask_email(e) for e in emails[:5]]
        if len(emails) > 5:
            masked_emails.append("...")
        
        await self.log(
            event_type,
            user_id=user_id,
            ip_address=ip_address,
            resource="accounts",
            action=event_type.value,
            details={
                "count": len(emails),
                "emails_masked": masked_emails,  # 使用脱敏后的邮件
                **(details or {}),
            },
        )


# 全局审计日志器
audit_logger = AuditLogger()


def init_audit_logger(db_manager):
    """初始化审计日志器（在应用启动时调用）"""
    global audit_logger
    audit_logger = AuditLogger(db_manager)
