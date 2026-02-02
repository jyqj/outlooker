"""
核心模块
包含异常处理、消息常量、频率限制等通用功能
"""

from .decorators import (
    handle_exceptions,
)
from .exceptions import (
    AccountLockedError,
    AccountNotFoundError,
    AppException,
    AuthenticationError,
    AuthorizationError,
    ConfigurationError,
    DatabaseConnectionError,
    DatabaseError,
    DuplicateEntryError,
    EmailNotFoundError,
    ExternalServiceError,
    IMAPAuthenticationError,
    IMAPConnectionError,
    IMAPError,
    InvalidCredentialsError,
    InvalidEmailFormatError,
    InvalidTokenError,
    RateLimitExceededError,
    ResourceNotFoundError,
    ServiceUnavailableError,
    TokenExpiredError,
    TokenRefreshError,
    ValidationError,
)
from .messages import (
    ERROR_ACCOUNT_CREATE_FAILED,
    ERROR_ACCOUNT_DELETE_FAILED,
    ERROR_ACCOUNT_EXISTS,
    ERROR_ACCOUNT_NOT_EXISTS,
    ERROR_ACCOUNT_UPDATE_FAILED,
    ERROR_AUTH_FAILED,
    ERROR_AUTH_INVALID_FORMAT,
    ERROR_AUTH_INVALID_TOKEN,
    ERROR_AUTH_MISSING_USER,
    # 错误消息 - 认证相关
    ERROR_AUTH_NO_TOKEN,
    ERROR_CONFIG_INVALID_VALUE,
    # 错误消息 - 系统配置相关
    ERROR_CONFIG_UPDATE_FAILED,
    ERROR_EMAIL_CONNECTION_FAILED,
    ERROR_EMAIL_INVALID,
    ERROR_EMAIL_LIMIT_INVALID,
    # 错误消息 - 账户相关
    ERROR_EMAIL_NOT_CONFIGURED,
    ERROR_EMAIL_NOT_PROVIDED,
    ERROR_EXPORT_FAILED,
    ERROR_EXPORT_NO_ACCOUNTS,
    # 错误消息 - 导入导出相关
    ERROR_IMPORT_FAILED,
    ERROR_IMPORT_NO_DATA,
    ERROR_IMPORT_PARSE_FAILED,
    ERROR_MESSAGE_NOT_FOUND,
    # 错误消息 - 邮件相关
    ERROR_MESSAGES_FETCH_FAILED,
    ERROR_REFRESH_TOKEN_EXPIRED,
    ERROR_REFRESH_TOKEN_INVALID,
    ERROR_TAGS_EMAIL_MISMATCH,
    # 错误消息 - 标签相关
    ERROR_TAGS_GET_FAILED,
    ERROR_TAGS_SET_FAILED,
    INFO_CONNECTION_SUCCESS,
    # 信息提示
    INFO_NO_MESSAGES,
    INFO_PARSING_SUCCESS,
    # 成功消息
    SUCCESS_ACCOUNT_CREATED,
    SUCCESS_ACCOUNT_DELETED,
    SUCCESS_ACCOUNT_UPDATED,
    SUCCESS_CONFIG_UPDATED,
    SUCCESS_EXPORT_COMPLETED,
    SUCCESS_IMPORT_COMPLETED,
    SUCCESS_TAGS_SAVED,
)
from .metrics import (
    APIMetrics,
    api_metrics,
    http_requests_total,
    http_request_duration_seconds,
    email_fetch_total,
    get_metrics,
    get_metrics_content_type,
)
from .middleware import (
    MetricsMiddleware,
)
from .audit import (
    AuditEvent,
    AuditEventType,
    AuditLogger,
    audit_logger,
    init_audit_logger,
)
from .rate_limiter import (
    AUDIT_LOG_FILE,
    LoginAuditor,
    LoginRateLimiter,
    auditor,
    public_api_rate_limiter,  # 现为 SlidingWindowRateLimiter 实例
    rate_limiter,
)
from .sliding_window_limiter import (
    RateLimitConfig,
    SlidingWindowRateLimiter,
    check_login_rate_limit,
    check_public_api_rate_limit,
    login_limiter,
    public_api_limiter,
)
from .logging_config import (
    get_logger,
    request_logger,
    setup_structured_logging,
)
from .startup import (
    log_startup_info,
    setup_app,
    validate_environment,
)

__all__ = [
    # Exceptions
    "AppException",
    "AuthenticationError",
    "TokenExpiredError",
    "InvalidTokenError",
    "InvalidCredentialsError",
    "AuthorizationError",
    "RateLimitExceededError",
    "AccountLockedError",
    "ResourceNotFoundError",
    "AccountNotFoundError",
    "EmailNotFoundError",
    "IMAPError",
    "IMAPConnectionError",
    "IMAPAuthenticationError",
    "TokenRefreshError",
    "DatabaseError",
    "DatabaseConnectionError",
    "DuplicateEntryError",
    "ValidationError",
    "InvalidEmailFormatError",
    "ConfigurationError",
    "ServiceUnavailableError",
    "ExternalServiceError",
    # Audit Logger
    "AuditEvent",
    "AuditEventType",
    "AuditLogger",
    "audit_logger",
    "init_audit_logger",
    # Rate Limiter - 登录相关
    "LoginRateLimiter",
    "LoginAuditor",  # 已重构为 AuditLogger 适配器
    "rate_limiter",
    "auditor",
    # Rate Limiter - API 限流（统一为 SlidingWindowRateLimiter）
    "public_api_rate_limiter",  # SlidingWindowRateLimiter 实例
    # Sliding Window Rate Limiter
    "RateLimitConfig",
    "SlidingWindowRateLimiter",
    "check_login_rate_limit",
    "check_public_api_rate_limit",
    "login_limiter",
    "public_api_limiter",
    # Decorators
    "handle_exceptions",
    # Metrics
    "APIMetrics",
    "api_metrics",
    "http_requests_total",
    "http_request_duration_seconds",
    "email_fetch_total",
    "get_metrics",
    "get_metrics_content_type",
    # Middleware
    "MetricsMiddleware",
    # Startup
    "validate_environment",
    "log_startup_info",
    "setup_app",
    # Logging
    "setup_structured_logging",
    "get_logger",
    "request_logger",
]
