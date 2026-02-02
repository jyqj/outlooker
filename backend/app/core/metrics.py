#!/usr/bin/env python3
"""
Prometheus metrics for application monitoring.

Also includes the original APIMetrics class for internal stats collection.
"""

import time
from collections import defaultdict
from dataclasses import dataclass, field
from functools import wraps
from threading import Lock
from typing import Callable

try:
    from prometheus_client import Counter, Gauge, Histogram, Info, generate_latest, CONTENT_TYPE_LATEST
    PROMETHEUS_AVAILABLE = True
except ImportError:
    PROMETHEUS_AVAILABLE = False
    # 创建占位符
    class Counter:
        def __init__(self, *args, **kwargs): pass
        def labels(self, *args, **kwargs): return self
        def inc(self, *args): pass
    
    class Gauge:
        def __init__(self, *args, **kwargs): pass
        def labels(self, *args, **kwargs): return self
        def set(self, *args): pass
        def inc(self, *args): pass
        def dec(self, *args): pass
    
    class Histogram:
        def __init__(self, *args, **kwargs): pass
        def labels(self, *args, **kwargs): return self
        def observe(self, *args): pass
    
    class Info:
        def __init__(self, *args, **kwargs): pass
        def info(self, *args): pass
    
    def generate_latest(*args): return b""
    CONTENT_TYPE_LATEST = "text/plain"


# ==================== 应用信息 ====================

app_info = Info(
    "outlooker_app",
    "Application information"
)

# ==================== HTTP 请求指标 ====================

http_requests_total = Counter(
    "outlooker_http_requests_total",
    "Total HTTP requests",
    ["method", "endpoint", "status_code"]
)

http_request_duration_seconds = Histogram(
    "outlooker_http_request_duration_seconds",
    "HTTP request duration in seconds",
    ["method", "endpoint"],
    buckets=[0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0]
)

http_requests_in_progress = Gauge(
    "outlooker_http_requests_in_progress",
    "HTTP requests currently in progress",
    ["method", "endpoint"]
)

# ==================== 邮件服务指标 ====================

email_fetch_total = Counter(
    "outlooker_email_fetch_total",
    "Total email fetch operations",
    ["status"]  # success, error, cache_hit
)

def _get_histogram_buckets() -> list[float]:
    """延迟获取 histogram buckets，避免循环导入"""
    try:
        from ..settings import get_settings
        return get_settings().metrics_histogram_buckets
    except Exception:
        # 导入失败时使用默认值
        return [0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0]


email_fetch_duration_seconds = Histogram(
    "outlooker_email_fetch_duration_seconds",
    "Email fetch duration in seconds",
    buckets=_get_histogram_buckets()
)

imap_connections_active = Gauge(
    "outlooker_imap_connections_active",
    "Active IMAP connections"
)

email_cache_size = Gauge(
    "outlooker_email_cache_size",
    "Number of cached emails"
)

email_cache_hit_rate = Gauge(
    "outlooker_email_cache_hit_rate",
    "Email cache hit rate"
)

# ==================== 账户指标 ====================

accounts_total = Gauge(
    "outlooker_accounts_total",
    "Total number of accounts",
    ["status"]  # active, deleted, used
)

account_operations_total = Counter(
    "outlooker_account_operations_total",
    "Total account operations",
    ["operation"]  # import, delete, update, tag
)

# ==================== 认证指标 ====================

auth_attempts_total = Counter(
    "outlooker_auth_attempts_total",
    "Total authentication attempts",
    ["result"]  # success, failed, locked
)

auth_active_sessions = Gauge(
    "outlooker_auth_active_sessions",
    "Number of active admin sessions"
)

# ==================== 速率限制指标 ====================

rate_limit_hits_total = Counter(
    "outlooker_rate_limit_hits_total",
    "Total rate limit hits",
    ["limiter"]  # login, public_api
)

# ==================== 辅助函数 ====================

def track_request_duration(endpoint: str):
    """装饰器：跟踪请求持续时间"""
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            method = "UNKNOWN"
            start_time = time.time()
            
            http_requests_in_progress.labels(method=method, endpoint=endpoint).inc()
            
            try:
                result = await func(*args, **kwargs)
                status = "200"
                return result
            except Exception as e:
                status = "500"
                raise
            finally:
                duration = time.time() - start_time
                http_requests_in_progress.labels(method=method, endpoint=endpoint).dec()
                http_request_duration_seconds.labels(method=method, endpoint=endpoint).observe(duration)
                http_requests_total.labels(method=method, endpoint=endpoint, status_code=status).inc()
        
        return wrapper
    return decorator


def update_email_metrics(
    cache_hits: int,
    cache_misses: int,
    active_connections: int,
    cached_emails: int
) -> None:
    """更新邮件服务指标"""
    total = cache_hits + cache_misses
    if total > 0:
        email_cache_hit_rate.set(cache_hits / total)
    
    imap_connections_active.set(active_connections)
    email_cache_size.set(cached_emails)


def update_account_metrics(
    active: int,
    deleted: int,
    used: int
) -> None:
    """更新账户指标"""
    accounts_total.labels(status="active").set(active)
    accounts_total.labels(status="deleted").set(deleted)
    accounts_total.labels(status="used").set(used)


def get_metrics() -> bytes:
    """获取 Prometheus 格式的指标"""
    if PROMETHEUS_AVAILABLE:
        return generate_latest()
    return b"# Prometheus client not installed\n"


def get_metrics_content_type() -> str:
    """获取指标内容类型"""
    return CONTENT_TYPE_LATEST


# ==================== 原有 API 指标收集器（保持兼容性）====================

def _get_max_samples() -> int:
    """延迟获取 max samples，避免循环导入"""
    try:
        from ..settings import get_settings
        return get_settings().metrics_max_samples
    except Exception:
        # 导入失败时使用默认值
        return 1000


@dataclass
class APIMetrics:
    """API 性能指标收集器"""

    request_counts: dict[str, int] = field(default_factory=lambda: defaultdict(int))
    response_times: dict[str, list[float]] = field(default_factory=lambda: defaultdict(list))
    error_counts: dict[str, int] = field(default_factory=lambda: defaultdict(int))
    _lock: Lock = field(default_factory=Lock, repr=False)
    _max_samples: int | None = field(default=None, repr=False)

    @property
    def max_samples_per_endpoint(self) -> int:
        """延迟获取 max_samples，避免循环导入"""
        if self._max_samples is not None:
            return self._max_samples
        return _get_max_samples()

    def record_request(self, endpoint: str, duration: float, success: bool) -> None:
        """记录一次请求
        
        Args:
            endpoint: API 端点路径
            duration: 响应时间（秒）
            success: 是否成功（状态码 < 400）
        """
        with self._lock:
            self.request_counts[endpoint] += 1

            times = self.response_times[endpoint]
            times.append(duration)
            # 保持样本数量在限制内
            max_samples = self.max_samples_per_endpoint
            if len(times) > max_samples:
                self.response_times[endpoint] = times[-max_samples:]

            if not success:
                self.error_counts[endpoint] += 1

    def get_stats(self) -> dict[str, dict]:
        """获取所有端点的统计信息"""
        with self._lock:
            stats = {}
            for endpoint in self.request_counts:
                times = self.response_times.get(endpoint, [])
                count = self.request_counts[endpoint]
                errors = self.error_counts.get(endpoint, 0)

                stats[endpoint] = {
                    "request_count": count,
                    "error_count": errors,
                    "error_rate": round(errors / count * 100, 2) if count > 0 else 0,
                    "avg_response_ms": round(sum(times) / len(times) * 1000, 2) if times else 0,
                    "min_response_ms": round(min(times) * 1000, 2) if times else 0,
                    "max_response_ms": round(max(times) * 1000, 2) if times else 0,
                }
            return stats

    def reset(self) -> None:
        """重置所有统计数据"""
        with self._lock:
            self.request_counts.clear()
            self.response_times.clear()
            self.error_counts.clear()


# 全局指标实例
api_metrics = APIMetrics()
