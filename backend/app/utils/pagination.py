#!/usr/bin/env python3
"""
通用分页与文本规范化工具

这些函数设计为纯函数，方便在 routers 和 services 中复用，
避免在各处重复实现分页、搜索与邮箱规范化逻辑。
"""

from __future__ import annotations

from typing import List, Optional, Sequence, Tuple, TypeVar


T = TypeVar("T")


def normalize_email(email: str) -> str:
    """统一规范邮箱字符串: 去除首尾空白并转为小写。

    仅负责简单的格式规范化，不做合法性校验。
    """
    return (email or "").strip().lower()


def paginate_items(items: Sequence[T], page: int, page_size: int) -> Tuple[List[T], int]:
    """对列表进行分页并返回切片结果与总数。

    Args:
        items: 待分页的数据序列
        page: 页码（从 1 开始）
        page_size: 每页数量

    Returns:
        (当前页数据列表, 总记录数)
    """
    # 兜底保护，避免非法页码导致异常
    page = max(1, page)
    page_size = max(1, page_size)

    total = len(items)
    start = (page - 1) * page_size
    end = start + page_size
    # 转为 list，保证返回类型稳定
    return list(items[start:end]), total


def filter_messages_by_search(messages: Sequence[dict], search: Optional[str]) -> List[dict]:
    """根据搜索关键字过滤邮件列表。

    匹配范围:
    - subject
    - from.emailAddress.address
    - bodyPreview
    """
    if not search:
        return list(messages)

    kw = search.lower()
    filtered: List[dict] = []

    for msg in messages:
        subject = (msg.get("subject") or "").lower()
        sender = (
            msg.get("from", {})
            .get("emailAddress", {})
            .get("address", "")
            .lower()
        )
        preview = (msg.get("bodyPreview") or "").lower()

        if kw in subject or kw in sender or kw in preview:
            filtered.append(msg)

    return filtered


__all__ = ["normalize_email", "paginate_items", "filter_messages_by_search"]



