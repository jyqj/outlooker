#!/usr/bin/env python3
"""
API 性能指标收集模块

提供简单的请求计数、响应时间和错误率统计
"""

from collections import defaultdict
from dataclasses import dataclass, field
from threading import Lock


@dataclass
class APIMetrics:
    """API 性能指标收集器"""

    request_counts: dict[str, int] = field(default_factory=lambda: defaultdict(int))
    response_times: dict[str, list[float]] = field(default_factory=lambda: defaultdict(list))
    error_counts: dict[str, int] = field(default_factory=lambda: defaultdict(int))
    _lock: Lock = field(default_factory=Lock, repr=False)

    # 限制每个端点保留的响应时间样本数
    MAX_SAMPLES_PER_ENDPOINT = 1000

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
            if len(times) > self.MAX_SAMPLES_PER_ENDPOINT:
                self.response_times[endpoint] = times[-self.MAX_SAMPLES_PER_ENDPOINT:]

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
