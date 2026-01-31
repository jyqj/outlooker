#!/usr/bin/env python3
"""
统一异常处理装饰器模块

提供可复用的异常处理装饰器，减少 Router 中的重复代码
"""

import logging
from collections.abc import Callable
from functools import wraps
from typing import Any, TypeVar

from fastapi import HTTPException

from .exceptions import AppException, DatabaseError

logger = logging.getLogger(__name__)

F = TypeVar("F", bound=Callable[..., Any])


def handle_exceptions(operation_name: str) -> Callable[[F], F]:
    """统一异常处理装饰器
    
    自动捕获异常并转换为适当的 API 响应：
    - HTTPException 和 AppException 直接抛出
    - 其他异常记录日志并转换为 DatabaseError
    
    Args:
        operation_name: 操作名称，用于日志记录
        
    Usage:
        @router.get("/api/example")
        @handle_exceptions("获取示例")
        async def get_example():
            ...
    """
    def decorator(func: F) -> F:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except (HTTPException, AppException):
                raise
            except Exception as e:
                logger.exception(f"{operation_name}失败: {e}")
                raise DatabaseError(message=f"{operation_name}失败")
        return wrapper  # type: ignore
    return decorator
