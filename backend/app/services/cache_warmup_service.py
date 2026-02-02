"""
缓存预热服务

提供并发控制的邮件缓存预热功能，用于账户导入后的异步预热。
"""

from __future__ import annotations

import asyncio
import logging
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from ..settings import get_settings

logger = logging.getLogger(__name__)
_settings = get_settings()


@dataclass
class WarmupStats:
    """预热统计信息"""

    pending: int = 0
    in_progress: int = 0
    success: int = 0
    failed: int = 0
    total_enqueued: int = 0
    last_updated_at: str | None = None
    errors: deque[dict[str, str]] = field(default_factory=lambda: deque(maxlen=50))

    def to_dict(self) -> dict[str, Any]:
        # deque 不支持切片，使用 list() 转换后取最后 10 条
        recent_errors = list(self.errors)[-10:] if self.errors else []
        return {
            "pending": self.pending,
            "in_progress": self.in_progress,
            "success": self.success,
            "failed": self.failed,
            "total_enqueued": self.total_enqueued,
            "last_updated_at": self.last_updated_at,
            "recent_errors": recent_errors,
        }


class CacheWarmupService:
    """缓存预热服务

    使用信号量控制并发数量，后台异步执行缓存预热任务。
    """

    def __init__(self, max_concurrent: int | None = None):
        """初始化缓存预热服务

        Args:
            max_concurrent: 最大并发数，默认从配置读取
        """
        self._max_concurrent = max_concurrent or _settings.cache_warmup_concurrency
        self._semaphore: asyncio.Semaphore | None = None
        self._semaphore_loop: asyncio.AbstractEventLoop | None = None
        self._stats = WarmupStats()
        self._lock: asyncio.Lock | None = None
        self._lock_loop: asyncio.AbstractEventLoop | None = None
        self._running_tasks: set[asyncio.Task] = set()

    def _get_semaphore(self) -> asyncio.Semaphore:
        """获取或创建信号量（处理事件循环切换）"""
        current_loop = asyncio.get_running_loop()
        if self._semaphore is None or self._semaphore_loop is not current_loop:
            self._semaphore = asyncio.Semaphore(self._max_concurrent)
            self._semaphore_loop = current_loop
        return self._semaphore

    def _get_lock(self) -> asyncio.Lock:
        """获取或创建锁（处理事件循环切换）"""
        current_loop = asyncio.get_running_loop()
        if self._lock is None or self._lock_loop is not current_loop:
            self._lock = asyncio.Lock()
            self._lock_loop = current_loop
        return self._lock

    async def _warmup_single_account(self, email: str, limit: int) -> bool:
        """预热单个账户的邮件缓存

        Args:
            email: 邮箱地址
            limit: 预热邮件数量

        Returns:
            是否成功
        """
        # 延迟导入避免循环依赖
        from .email_service import email_manager

        try:
            await email_manager.get_messages(email, top=limit, folder=None, force_refresh=False)
            return True
        except Exception as exc:
            logger.warning("预热缓存失败(%s): %s", email, exc)
            async with self._get_lock():
                self._stats.errors.append({
                    "email": email,
                    "error": str(exc),
                    "time": datetime.now(timezone.utc).isoformat(),
                })
            return False

    async def _process_email(self, email: str, limit: int) -> None:
        """处理单个邮箱的预热任务（带信号量控制）"""
        async with self._get_lock():
            self._stats.pending -= 1
            self._stats.in_progress += 1
            self._stats.last_updated_at = datetime.now(timezone.utc).isoformat()

        try:
            async with self._get_semaphore():
                success = await self._warmup_single_account(email, limit)

            async with self._get_lock():
                self._stats.in_progress -= 1
                if success:
                    self._stats.success += 1
                else:
                    self._stats.failed += 1
                self._stats.last_updated_at = datetime.now(timezone.utc).isoformat()

        except Exception as exc:
            logger.error("处理预热任务异常(%s): %s", email, exc)
            async with self._get_lock():
                self._stats.in_progress -= 1
                self._stats.failed += 1
                self._stats.last_updated_at = datetime.now(timezone.utc).isoformat()

    async def enqueue_warmup(self, emails: list[str], limit: int = 5) -> int:
        """将邮箱列表加入预热队列

        Args:
            emails: 需要预热的邮箱列表
            limit: 每个邮箱预热的邮件数量

        Returns:
            加入队列的邮箱数量
        """
        if not emails:
            return 0

        async with self._get_lock():
            self._stats.pending += len(emails)
            self._stats.total_enqueued += len(emails)
            self._stats.last_updated_at = datetime.now(timezone.utc).isoformat()

        logger.info(
            "开始后台预热邮件缓存，共 %d 个账户，并发数: %d",
            len(emails),
            self._max_concurrent,
        )

        # 创建所有任务并发执行（信号量会自动控制并发数）
        tasks = [self._process_email(email, limit) for email in emails]
        
        # 使用 gather 并发执行，但不等待完成（后台执行）
        warmup_task = asyncio.create_task(self._run_warmup_tasks(tasks))
        self._running_tasks.add(warmup_task)
        warmup_task.add_done_callback(self._running_tasks.discard)

        return len(emails)

    async def _run_warmup_tasks(self, tasks: list) -> None:
        """后台执行预热任务"""
        try:
            results = await asyncio.gather(*tasks, return_exceptions=True)
            # 检查并记录异常
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    logger.error("预热任务执行异常: %s", result, exc_info=result)
            logger.info(
                "邮件缓存预热完成: 成功 %d，失败 %d，总计 %d",
                self._stats.success,
                self._stats.failed,
                self._stats.total_enqueued,
            )
        except Exception as exc:
            logger.error("预热任务批量执行异常: %s", exc, exc_info=exc)

    def get_stats(self) -> dict[str, Any]:
        """获取当前预热统计信息"""
        return self._stats.to_dict()

    def reset_stats(self) -> None:
        """重置统计信息"""
        self._stats = WarmupStats()

    async def cleanup(self) -> None:
        """清理资源，取消所有运行中的任务"""
        if not self._running_tasks:
            return
        
        logger.info("正在清理缓存预热服务，取消 %d 个运行中的任务", len(self._running_tasks))
        for task in self._running_tasks.copy():
            if not task.done():
                task.cancel()
        
        # 等待所有任务完成或取消
        if self._running_tasks:
            await asyncio.gather(*self._running_tasks, return_exceptions=True)
        
        self._running_tasks.clear()
        logger.info("缓存预热服务清理完成")


# 全局单例
cache_warmup_service = CacheWarmupService()


def schedule_cache_warmup(emails: list[str], limit: int = 5) -> None:
    """调度后台缓存预热任务（非阻塞）

    这是对外暴露的便捷函数，用于替代旧的串行预热逻辑。

    Args:
        emails: 需要预热的邮箱列表
        limit: 每个邮箱预热的邮件数量
    """
    if not emails:
        return

    try:
        loop = asyncio.get_running_loop()
        loop.create_task(cache_warmup_service.enqueue_warmup(emails, limit))
        logger.info("已调度缓存预热任务: %d 个账户", len(emails))
    except RuntimeError:
        # 没有运行中的事件循环，忽略预热
        logger.debug("无法调度缓存预热任务：没有运行中的事件循环")
