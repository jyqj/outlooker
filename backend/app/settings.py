#!/usr/bin/env python3
"""
Application settings powered by pydantic-settings.
"""

from pathlib import Path
from functools import lru_cache
from typing import List, Optional
import logging

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parents[2]
logger = logging.getLogger(__name__)


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

    # OAuth / IMAP
    client_id: Optional[str] = Field(default=None, alias="CLIENT_ID")
    token_url: str = Field(
        default="https://login.microsoftonline.com/consumers/oauth2/v2.0/token",
        alias="TOKEN_URL",
    )
    imap_server: str = Field(default="outlook.live.com", alias="IMAP_SERVER")
    imap_port: int = Field(default=993, alias="IMAP_PORT")
    inbox_folder_name: str = Field(default="INBOX", alias="INBOX_FOLDER_NAME")
    junk_folder_name: str = Field(default="Junk", alias="JUNK_FOLDER_NAME")

    # Admin / auth
    admin_username: Optional[str] = Field(default=None, alias="ADMIN_USERNAME")
    admin_password: Optional[str] = Field(default=None, alias="ADMIN_PASSWORD")
    legacy_admin_token: Optional[str] = Field(default=None, alias="LEGACY_ADMIN_TOKEN")
    enable_legacy_admin_token: bool = Field(default=False, alias="ENABLE_LEGACY_ADMIN_TOKEN")
    jwt_secret_key: Optional[str] = Field(default=None, alias="JWT_SECRET_KEY")
    access_token_expire_minutes: int = Field(default=60 * 24, alias="ACCESS_TOKEN_EXPIRE_MINUTES")

    # API / UI
    allowed_origins: List[str] = Field(
        default=["http://localhost:5173", "http://localhost:5001"],
        alias="ALLOWED_ORIGINS",
    )
    default_email_limit: int = Field(default=1, alias="DEFAULT_EMAIL_LIMIT")
    max_email_limit: int = Field(default=50, alias="MAX_EMAIL_LIMIT")

    # Storage paths relative to project root
    database_path: str = Field(default="data/outlook_manager.db", alias="DATABASE_PATH")
    logs_dir: str = Field(default="data/logs", alias="LOGS_DIR")
    static_dir: str = Field(default="data/static", alias="STATIC_DIR")

    data_encryption_key: Optional[str] = Field(default=None, alias="DATA_ENCRYPTION_KEY")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")

    @staticmethod
    def _env(info) -> str:
        return (info.data.get("app_env") or "development").lower()

    @field_validator("jwt_secret_key", mode="after")
    @classmethod
    def validate_jwt_secret_key(cls, value: Optional[str], info):
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
    def validate_data_encryption_key(cls, value: Optional[str], info):
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
    def validate_client_id(cls, value: Optional[str], info):
        """生产环境要求显式配置 CLIENT_ID"""
        app_env = cls._env(info)
        if value:
            return value
        if app_env == "production":
            raise ValueError("在生产环境中必须配置 CLIENT_ID")
        fallback = "dbc8e03a-b00c-46bd-ae65-b683e7707cb0"
        logger.warning("未设置 CLIENT_ID，开发环境使用示例值")
        return fallback

    @field_validator("legacy_admin_token", mode="after")
    @classmethod
    def validate_legacy_token(cls, value: Optional[str], info):
        """保证 Legacy Token 仅在安全前提下被启用"""
        enable_legacy = info.data.get("enable_legacy_admin_token") or False
        if not enable_legacy:
            return value
        if not value:
            raise ValueError("启用了 ENABLE_LEGACY_ADMIN_TOKEN 必须提供 LEGACY_ADMIN_TOKEN")
        if value == "admin123":
            raise ValueError("LEGACY_ADMIN_TOKEN 禁止使用默认值 admin123")
        return value

    @field_validator("jwt_secret_key", "data_encryption_key", mode="after")
    @classmethod
    def ensure_min_length(cls, value: str, info):
        """简单的长度检查"""
        if not value or len(value) < 16:
            raise ValueError(f"{info.field_name} 长度必须至少 16 字符")
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
