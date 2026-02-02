#!/usr/bin/env python3
"""
Application settings powered by pydantic-settings.

配置采用嵌套模型组织，支持分组访问和向后兼容的平坦访问：
- settings.imap.server / settings.imap_server (向后兼容)
- settings.cache.email_ttl_seconds / settings.email_cache_ttl_seconds (向后兼容)
- settings.rate_limit.max_login_attempts / settings.max_login_attempts (向后兼容)
- settings.email.default_limit / settings.default_email_limit (向后兼容)
"""

import logging
from functools import lru_cache
from pathlib import Path

from pydantic import BaseModel, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parents[2]
logger = logging.getLogger(__name__)


# ============================================================================
# 嵌套配置模型
# ============================================================================


class IMAPConfig(BaseModel):
    """IMAP 相关配置"""

    server: str = "outlook.live.com"
    port: int = 993
    buffer_time_seconds: int = 300
    token_expire_seconds: int = 3600
    connection_timeout: int = 30
    operation_timeout: int = 10
    max_retries: int = 3
    inbox_folder: str = "INBOX"
    junk_folder: str = "Junk"


class CacheConfig(BaseModel):
    """缓存相关配置"""

    email_ttl_seconds: int = 15
    limit_per_account: int = 100
    warmup_concurrency: int = 5


class RateLimitConfig(BaseModel):
    """速率限制配置"""

    max_login_attempts: int = 5
    lockout_duration_seconds: int = 900
    login_attempt_window_seconds: int = 300
    public_api_rate_limit: int = 60


class EmailConfig(BaseModel):
    """邮件相关配置"""

    default_limit: int = 5
    max_limit: int = 50
    min_limit: int = 1


class PaginationConfig(BaseModel):
    """分页配置"""

    default_page_size: int = 10
    max_page_size: int = 100


class AuthConfig(BaseModel):
    """认证相关配置"""

    access_token_expire_minutes: int = 60
    refresh_token_expire_days: int = 7


class StorageConfig(BaseModel):
    """存储路径配置"""

    database_path: str = "data/outlook_manager.db"
    logs_dir: str = "data/logs"
    static_dir: str = "data/static"


# ============================================================================
# 主配置类
# ============================================================================


class AppSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(
            str(PROJECT_ROOT / ".env"),
            str(PROJECT_ROOT / "backend/.env"),
        ),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_env: str = Field(default="development", alias="APP_ENV")

    @property
    def is_production(self) -> bool:
        return self.app_env.lower() == "production"

    # ========================================================================
    # OAuth 配置
    # ========================================================================
    client_id: str | None = Field(default=None, alias="CLIENT_ID")
    token_url: str = Field(
        default="https://login.microsoftonline.com/consumers/oauth2/v2.0/token",
        alias="TOKEN_URL",
    )

    # ========================================================================
    # 原始配置字段（环境变量映射，保持向后兼容）
    # ========================================================================

    # IMAP 配置 (环境变量映射)
    imap_server: str = Field(default="outlook.live.com", alias="IMAP_SERVER")
    imap_port: int = Field(default=993, alias="IMAP_PORT")
    inbox_folder_name: str = Field(default="INBOX", alias="INBOX_FOLDER_NAME")
    junk_folder_name: str = Field(default="Junk", alias="JUNK_FOLDER_NAME")
    imap_buffer_time_seconds: int = Field(default=300, alias="IMAP_BUFFER_TIME_SECONDS")
    imap_token_expire_seconds: int = Field(default=3600, alias="IMAP_TOKEN_EXPIRE_SECONDS")
    imap_connection_timeout: int = Field(default=30, alias="IMAP_CONNECTION_TIMEOUT")
    imap_operation_timeout: int = Field(default=10, alias="IMAP_OPERATION_TIMEOUT")
    imap_max_retries: int = Field(default=3, alias="IMAP_MAX_RETRIES")

    # Admin / auth
    admin_username: str | None = Field(default=None, alias="ADMIN_USERNAME")
    admin_password: str | None = Field(default=None, alias="ADMIN_PASSWORD")
    jwt_secret_key: str | None = Field(default=None, alias="JWT_SECRET_KEY")
    access_token_expire_minutes: int = Field(default=60 * 24, alias="ACCESS_TOKEN_EXPIRE_MINUTES")
    refresh_token_expire_days: int = Field(default=7, alias="REFRESH_TOKEN_EXPIRE_DAYS")

    # API / UI
    allowed_origins: list[str] = Field(
        default=["http://localhost:5173", "http://localhost:5001"],
        alias="ALLOWED_ORIGINS",
    )
    default_email_limit: int = Field(default=5, alias="DEFAULT_EMAIL_LIMIT")
    max_email_limit: int = Field(default=50, alias="MAX_EMAIL_LIMIT")
    min_email_limit: int = Field(default=1, alias="MIN_EMAIL_LIMIT")
    email_cache_ttl_seconds: int = Field(default=15, alias="EMAIL_CACHE_TTL_SECONDS")

    # Storage paths relative to project root
    database_path: str = Field(default="data/outlook_manager.db", alias="DATABASE_PATH")
    logs_dir: str = Field(default="data/logs", alias="LOGS_DIR")
    static_dir: str = Field(default="data/static", alias="STATIC_DIR")

    # Rate limiting configuration
    max_login_attempts: int = Field(default=5, alias="MAX_LOGIN_ATTEMPTS")
    lockout_duration_seconds: int = Field(default=900, alias="LOCKOUT_DURATION_SECONDS")
    login_attempt_window_seconds: int = Field(default=300, alias="LOGIN_ATTEMPT_WINDOW_SECONDS")
    public_api_rate_limit: int = Field(default=60, alias="PUBLIC_API_RATE_LIMIT")

    # Email cache settings
    email_cache_limit_per_account: int = Field(default=100, alias="EMAIL_CACHE_LIMIT_PER_ACCOUNT")

    # Cache warmup settings
    cache_warmup_concurrency: int = Field(default=5, alias="CACHE_WARMUP_CONCURRENCY")

    # Pagination settings
    default_page_size: int = Field(default=10, alias="DEFAULT_PAGE_SIZE")
    max_page_size: int = Field(default=100, alias="MAX_PAGE_SIZE")

    # Performance / Pool 配置
    max_tracked_keys: int = Field(default=100000, alias="MAX_TRACKED_KEYS")
    db_thread_pool_size: int = Field(default=4, alias="DB_THREAD_POOL_SIZE")
    imap_pool_max_clients: int = Field(default=100, alias="IMAP_POOL_MAX_CLIENTS")
    metrics_max_samples: int = Field(default=1000, alias="METRICS_MAX_SAMPLES")
    metrics_histogram_buckets: list[float] = Field(
        default=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0],
        alias="METRICS_HISTOGRAM_BUCKETS",
    )

    data_encryption_key: str | None = Field(default=None, alias="DATA_ENCRYPTION_KEY")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    admin_refresh_cookie_enabled: bool = Field(default=True, alias="ADMIN_REFRESH_COOKIE")
    admin_refresh_cookie_name: str = Field(default="outlooker_rtk", alias="ADMIN_REFRESH_COOKIE_NAME")
    admin_refresh_cookie_secure: bool = Field(default=False, alias="ADMIN_REFRESH_COOKIE_SECURE")
    admin_refresh_cookie_path: str = Field(default="/", alias="ADMIN_REFRESH_COOKIE_PATH")
    public_api_token: str | None = Field(default=None, alias="PUBLIC_API_TOKEN")

    # ========================================================================
    # 嵌套配置模型访问器（分组访问）
    # ========================================================================

    @property
    def imap(self) -> IMAPConfig:
        """IMAP 配置分组"""
        return IMAPConfig(
            server=self.imap_server,
            port=self.imap_port,
            buffer_time_seconds=self.imap_buffer_time_seconds,
            token_expire_seconds=self.imap_token_expire_seconds,
            connection_timeout=self.imap_connection_timeout,
            operation_timeout=self.imap_operation_timeout,
            max_retries=self.imap_max_retries,
            inbox_folder=self.inbox_folder_name,
            junk_folder=self.junk_folder_name,
        )

    @property
    def cache(self) -> CacheConfig:
        """缓存配置分组"""
        return CacheConfig(
            email_ttl_seconds=self.email_cache_ttl_seconds,
            limit_per_account=self.email_cache_limit_per_account,
            warmup_concurrency=self.cache_warmup_concurrency,
        )

    @property
    def rate_limit(self) -> RateLimitConfig:
        """速率限制配置分组"""
        return RateLimitConfig(
            max_login_attempts=self.max_login_attempts,
            lockout_duration_seconds=self.lockout_duration_seconds,
            login_attempt_window_seconds=self.login_attempt_window_seconds,
            public_api_rate_limit=self.public_api_rate_limit,
        )

    @property
    def email(self) -> EmailConfig:
        """邮件配置分组"""
        return EmailConfig(
            default_limit=self.default_email_limit,
            max_limit=self.max_email_limit,
            min_limit=self.min_email_limit,
        )

    @property
    def pagination(self) -> PaginationConfig:
        """分页配置分组"""
        return PaginationConfig(
            default_page_size=self.default_page_size,
            max_page_size=self.max_page_size,
        )

    @property
    def auth(self) -> AuthConfig:
        """认证配置分组"""
        return AuthConfig(
            access_token_expire_minutes=self.access_token_expire_minutes,
            refresh_token_expire_days=self.refresh_token_expire_days,
        )

    @property
    def storage(self) -> StorageConfig:
        """存储配置分组"""
        return StorageConfig(
            database_path=self.database_path,
            logs_dir=self.logs_dir,
            static_dir=self.static_dir,
        )

    @staticmethod
    def _env(info) -> str:
        return (info.data.get("app_env") or "development").lower()

    @field_validator("jwt_secret_key", mode="after")
    @classmethod
    def validate_jwt_secret_key(cls, value: str | None, info):
        """生产环境要求显式配置 JWT_SECRET_KEY"""
        app_env = cls._env(info)
        if value:
            return value
        if app_env == "production":
            raise ValueError("在生产环境中必须配置安全的 JWT_SECRET_KEY")
        fallback = "dev-secret-key-change-me"
        logger.warning("未设置 JWT_SECRET_KEY，开发环境使用默认值，仅供本地调试")
        return fallback

    @field_validator("data_encryption_key", mode="after")
    @classmethod
    def validate_data_encryption_key(cls, value: str | None, info):
        """生产环境要求显式配置 DATA_ENCRYPTION_KEY"""
        app_env = cls._env(info)
        if value:
            return value
        if app_env == "production":
            raise ValueError("在生产环境中必须配置安全的 DATA_ENCRYPTION_KEY")
        fallback = "dev-encryption-key-change-me"
        logger.warning("未设置 DATA_ENCRYPTION_KEY，开发环境使用默认值，仅供本地调试")
        return fallback

    @field_validator("client_id", mode="after")
    @classmethod
    def validate_client_id(cls, value: str | None, info):
        """生产环境要求显式配置 CLIENT_ID"""
        app_env = cls._env(info)
        if value:
            return value
        if app_env == "production":
            raise ValueError("在生产环境中必须配置 CLIENT_ID")
        fallback = "dbc8e03a-b00c-46bd-ae65-b683e7707cb0"
        logger.warning("未设置 CLIENT_ID，开发环境使用示例值")
        return fallback

    @field_validator("jwt_secret_key", "data_encryption_key", mode="after")
    @classmethod
    def ensure_min_length(cls, value: str, info):
        """密钥强度检查"""
        if not value:
            raise ValueError(f"{info.field_name} 不能为空")
        
        # 最小长度要求
        min_length = 32 if cls._env(info) == "production" else 16
        if len(value) < min_length:
            raise ValueError(f"{info.field_name} 长度必须至少 {min_length} 字符")
        
        # 生产环境要求包含多种字符类型
        if cls._env(info) == "production":
            has_upper = any(c.isupper() for c in value)
            has_lower = any(c.islower() for c in value)
            has_digit = any(c.isdigit() for c in value)
            if not (has_upper and has_lower and has_digit):
                logger.warning(f"{info.field_name} 建议包含大小写字母和数字以提高安全性")
        
        return value

    @field_validator("public_api_token", mode="after")
    @classmethod
    def validate_public_api_token(cls, value: str | None, info):
        """公共接口调用口令：生产必填，开发提供示例值"""
        app_env = cls._env(info)
        if value:
            if len(value) < 12:
                raise ValueError("PUBLIC_API_TOKEN 长度必须至少 12 字符")
            return value
        if app_env == "production":
            raise ValueError("在生产环境中必须配置安全的 PUBLIC_API_TOKEN")
        fallback = "dev-public-token-change-me"
        logger.warning("未设置 PUBLIC_API_TOKEN，开发环境使用默认值，仅供本地调试")
        return fallback

    @field_validator("admin_refresh_cookie_secure", mode="after")
    @classmethod
    def validate_refresh_cookie_secure(cls, value: bool, info):
        """生产环境要求刷新 Cookie 开启 secure"""
        if cls._env(info) == "production" and not value:
            raise ValueError("生产环境必须启用 ADMIN_REFRESH_COOKIE_SECURE=true 以使用 HTTPS Cookie")
        return value

    @field_validator("allowed_origins", mode="before")
    @classmethod
    def split_origins(cls, value):
        if isinstance(value, list):
            return value
        if isinstance(value, str):
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return value


@lru_cache
def get_settings() -> AppSettings:
    return AppSettings()
