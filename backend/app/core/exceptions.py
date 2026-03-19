#!/usr/bin/env python3
"""
统一异常处理模块

定义应用自定义异常，确保错误处理和 API 响应的一致性。
"""

from typing import Any


class AppException(Exception):
    """应用异常基类"""

    def __init__(
        self,
        message: str,
        status_code: int = 400,
        error_code: str | None = None,
        details: dict[str, Any] | None = None,
    ):
        self.message = message
        self.status_code = status_code
        self.error_code = error_code or self.__class__.__name__
        self.details = details or {}
        super().__init__(self.message)

    def to_dict(self) -> dict[str, Any]:
        result = {
            "success": False,
            "message": self.message,
            "error_code": self.error_code,
        }
        if self.details:
            result["details"] = self.details
        return result


# ============================================================================
# 认证异常
# ============================================================================

class AuthenticationError(AppException):
    """认证失败"""

    def __init__(self, message: str = "认证失败", **kwargs):
        super().__init__(message, status_code=401, **kwargs)


class TokenExpiredError(AuthenticationError):
    """令牌已过期"""

    def __init__(self, message: str = "令牌已过期"):
        super().__init__(message, error_code="TOKEN_EXPIRED")


class InvalidTokenError(AuthenticationError):
    """无效令牌"""

    def __init__(self, message: str = "无效的令牌"):
        super().__init__(message, error_code="INVALID_TOKEN")


class InvalidCredentialsError(AuthenticationError):
    """凭证无效"""

    def __init__(self, message: str = "用户名或密码错误"):
        super().__init__(message, error_code="INVALID_CREDENTIALS")


# ============================================================================
# 授权异常
# ============================================================================

class AuthorizationError(AppException):
    """权限不足"""

    def __init__(self, message: str = "权限不足", **kwargs):
        super().__init__(message, status_code=403, **kwargs)


class RateLimitExceededError(AuthorizationError):
    """请求频率超限"""

    def __init__(
        self,
        message: str = "请求过于频繁，请稍后再试",
        retry_after: int | None = None,
    ):
        details = {"retry_after": retry_after} if retry_after else {}
        super().__init__(message, error_code="RATE_LIMIT_EXCEEDED", details=details)


class AccountLockedError(AuthorizationError):
    """账户已锁定"""

    def __init__(
        self,
        message: str = "账户已被临时锁定",
        lockout_remaining: int | None = None,
    ):
        details = {"lockout_remaining_seconds": lockout_remaining} if lockout_remaining else {}
        super().__init__(message, error_code="ACCOUNT_LOCKED", details=details)


# ============================================================================
# 资源异常
# ============================================================================

class ResourceNotFoundError(AppException):
    """资源未找到"""

    def __init__(
        self,
        message: str = "资源未找到",
        resource_type: str | None = None,
        resource_id: str | None = None,
    ):
        details = {}
        if resource_type:
            details["resource_type"] = resource_type
        if resource_id:
            details["resource_id"] = resource_id
        super().__init__(message, status_code=404, details=details)


class AccountNotFoundError(ResourceNotFoundError):
    """账户未找到"""

    def __init__(self, email: str):
        super().__init__(
            message=f"邮箱未在配置中找到: {email}",
            resource_type="account",
            resource_id=email,
        )


class EmailNotFoundError(ResourceNotFoundError):
    """邮件未找到"""

    def __init__(self, message_id: str):
        super().__init__(
            message=f"邮件未找到: {message_id}",
            resource_type="email",
            resource_id=message_id,
        )


# ============================================================================
# IMAP 异常
# ============================================================================

class IMAPError(AppException):
    """IMAP 操作异常基类"""

    def __init__(self, message: str = "IMAP 操作失败", **kwargs):
        super().__init__(message, status_code=502, **kwargs)


class IMAPConnectionError(IMAPError):
    """IMAP 连接失败"""

    def __init__(self, message: str = "无法连接到 IMAP 服务器"):
        super().__init__(message, error_code="IMAP_CONNECTION_FAILED")


class IMAPAuthenticationError(IMAPError):
    """IMAP 认证失败"""

    def __init__(self, message: str = "IMAP 认证失败"):
        super().__init__(message, error_code="IMAP_AUTH_FAILED")


class TokenRefreshError(IMAPError):
    """OAuth 令牌刷新失败"""

    def __init__(self, message: str = "刷新访问令牌失败"):
        super().__init__(message, error_code="TOKEN_REFRESH_FAILED")


# ============================================================================
# 数据库异常
# ============================================================================

class DatabaseError(AppException):
    """数据库操作异常基类"""

    def __init__(self, message: str = "数据库操作失败", **kwargs):
        super().__init__(message, status_code=500, **kwargs)


class DatabaseConnectionError(DatabaseError):
    """数据库连接失败"""

    def __init__(self, message: str = "无法连接到数据库"):
        super().__init__(message, error_code="DB_CONNECTION_FAILED")


class DuplicateEntryError(DatabaseError):
    """重复记录"""

    def __init__(self, message: str = "记录已存在"):
        super().__init__(message, status_code=409, error_code="DUPLICATE_ENTRY")


# ============================================================================
# 验证异常
# ============================================================================

class ValidationError(AppException):
    """输入验证失败"""

    def __init__(
        self,
        message: str = "数据验证失败",
        field: str | None = None,
        **kwargs,
    ):
        details = {"field": field} if field else {}
        super().__init__(message, status_code=422, details=details, **kwargs)


class InvalidEmailFormatError(ValidationError):
    """邮箱格式无效"""

    def __init__(self, email: str):
        super().__init__(
            message=f"邮箱格式无效: {email}",
            field="email",
            error_code="INVALID_EMAIL_FORMAT",
        )


class ConfigurationError(AppException):
    """配置错误"""

    def __init__(self, message: str = "配置错误", **kwargs):
        super().__init__(message, status_code=500, **kwargs)


# ============================================================================
# 服务异常
# ============================================================================

class ServiceUnavailableError(AppException):
    """服务暂不可用"""

    def __init__(self, message: str = "服务暂时不可用", **kwargs):
        super().__init__(message, status_code=503, **kwargs)


class ExternalServiceError(AppException):
    """外部服务调用失败"""

    def __init__(
        self,
        message: str = "外部服务调用失败",
        service_name: str | None = None,
        **kwargs,
    ):
        details = {"service": service_name} if service_name else {}
        super().__init__(message, status_code=502, details=details, **kwargs)
