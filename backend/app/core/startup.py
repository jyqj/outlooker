#!/usr/bin/env python3
"""
应用启动验证模块

在应用启动时执行必要的环境和配置检查
"""

import logging

from ..settings import get_settings
from .logging_config import get_logger, setup_structured_logging

logger = logging.getLogger(__name__)


def setup_app() -> None:
    """应用启动初始化
    
    在其他初始化之前调用，配置结构化日志等。
    """
    # 初始化结构化日志
    setup_structured_logging()
    
    # 获取结构化日志器
    struct_logger = get_logger("startup")
    struct_logger.info("structured_logging_initialized", message="结构化日志初始化完成")


def validate_environment() -> list[str]:
    """验证环境配置
    
    Returns:
        警告消息列表（空列表表示全部通过）
    """
    settings = get_settings()
    warnings: list[str] = []

    # 开发环境跳过严格检查
    if not settings.is_production:
        logger.info("开发环境模式，跳过严格配置检查")
        return warnings

    # 检查安全相关配置
    if settings.jwt_secret_key and settings.jwt_secret_key.endswith("change-me"):
        warnings.append("JWT_SECRET_KEY 使用了默认值")

    if settings.data_encryption_key and settings.data_encryption_key.endswith("change-me"):
        warnings.append("DATA_ENCRYPTION_KEY 使用了默认值")

    if settings.public_api_token and settings.public_api_token.endswith("change-me"):
        warnings.append("PUBLIC_API_TOKEN 使用了默认值")

    # 检查 CLIENT_ID
    if settings.client_id == "dbc8e03a-b00c-46bd-ae65-b683e7707cb0":
        warnings.append("CLIENT_ID 使用了示例值")

    # 检查 Cookie 安全设置
    if not settings.admin_refresh_cookie_secure:
        warnings.append("ADMIN_REFRESH_COOKIE_SECURE 未启用（生产环境应使用 HTTPS）")

    return warnings


def log_startup_info() -> None:
    """记录启动信息"""
    settings = get_settings()

    logger.info("=" * 50)
    logger.info("Outlooker 启动信息")
    logger.info("=" * 50)
    logger.info(f"环境: {settings.app_env}")
    logger.info(f"数据库: {settings.database_path}")
    logger.info(f"日志目录: {settings.logs_dir}")
    logger.info(f"静态目录: {settings.static_dir}")
    logger.info("=" * 50)
