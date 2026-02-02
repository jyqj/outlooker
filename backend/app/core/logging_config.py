#!/usr/bin/env python3
"""
Structured logging configuration using structlog.
"""

import logging
import sys
from typing import Any

import structlog
from structlog.typing import EventDict, WrappedLogger

from ..settings import get_settings


def add_app_context(
    logger: WrappedLogger, method_name: str, event_dict: EventDict
) -> EventDict:
    """添加应用上下文"""
    settings = get_settings()
    event_dict["app_env"] = settings.app_env
    event_dict["service"] = "outlooker"
    return event_dict


def setup_structured_logging() -> None:
    """配置结构化日志"""
    settings = get_settings()
    log_level = getattr(logging, settings.log_level.upper(), logging.INFO)
    
    # 根据环境选择渲染器
    if settings.is_production:
        # 生产环境：JSON 格式
        renderer = structlog.processors.JSONRenderer()
    else:
        # 开发环境：彩色控制台
        renderer = structlog.dev.ConsoleRenderer(colors=True)
    
    # 配置 structlog
    structlog.configure(
        processors=[
            # 添加日志级别
            structlog.stdlib.add_log_level,
            # 添加时间戳
            structlog.processors.TimeStamper(fmt="iso"),
            # 添加调用者信息
            structlog.processors.CallsiteParameterAdder(
                [
                    structlog.processors.CallsiteParameter.FILENAME,
                    structlog.processors.CallsiteParameter.LINENO,
                    structlog.processors.CallsiteParameter.FUNC_NAME,
                ]
            ),
            # 添加应用上下文
            add_app_context,
            # 展开异常
            structlog.processors.format_exc_info,
            # 选择渲染器
            renderer,
        ],
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )
    
    # 配置标准库 logging
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=log_level,
    )
    
    # 降低第三方库的日志级别
    for lib in ["httpx", "httpcore", "urllib3", "asyncio"]:
        logging.getLogger(lib).setLevel(logging.WARNING)


def get_logger(name: str | None = None) -> structlog.stdlib.BoundLogger:
    """获取结构化日志器"""
    return structlog.get_logger(name)


class RequestLogger:
    """请求日志记录器"""
    
    def __init__(self):
        self.logger = get_logger("request")
    
    def log_request(
        self,
        method: str,
        path: str,
        status_code: int,
        duration_ms: float,
        client_ip: str | None = None,
        user_id: str | None = None,
        extra: dict[str, Any] | None = None,
    ) -> None:
        """记录请求日志"""
        log_data = {
            "method": method,
            "path": path,
            "status_code": status_code,
            "duration_ms": round(duration_ms, 2),
            "client_ip": client_ip,
        }
        
        if user_id:
            log_data["user_id"] = user_id
        
        if extra:
            log_data.update(extra)
        
        # 根据状态码选择日志级别
        if status_code >= 500:
            self.logger.error("request_error", **log_data)
        elif status_code >= 400:
            self.logger.warning("request_client_error", **log_data)
        else:
            self.logger.info("request_success", **log_data)


request_logger = RequestLogger()
