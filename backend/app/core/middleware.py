#!/usr/bin/env python3
"""
HTTP 中间件模块

提供请求监控、性能追踪等中间件
"""

import logging
import time

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from .metrics import api_metrics

logger = logging.getLogger(__name__)


class MetricsMiddleware(BaseHTTPMiddleware):
    """API 性能监控中间件
    
    记录每个请求的响应时间和成功/失败状态
    """

    # 不需要监控的路径前缀
    EXCLUDED_PATHS = {"/docs", "/redoc", "/openapi.json", "/static", "/assets"}

    async def dispatch(self, request: Request, call_next) -> Response:
        # 跳过不需要监控的路径
        path = request.url.path
        if any(path.startswith(excluded) for excluded in self.EXCLUDED_PATHS):
            return await call_next(request)

        start_time = time.time()

        try:
            response = await call_next(request)
            duration = time.time() - start_time
            success = response.status_code < 400

            # 记录指标
            api_metrics.record_request(path, duration, success)

            # 慢请求警告（超过 1 秒）
            if duration > 1.0:
                logger.warning(
                    f"慢请求: {request.method} {path} 耗时 {duration*1000:.0f}ms"
                )

            return response

        except Exception:
            duration = time.time() - start_time
            api_metrics.record_request(path, duration, False)
            raise
