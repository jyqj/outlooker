#!/usr/bin/env python3
"""
HTTP 请求相关工具函数
"""

from fastapi import Request


def get_client_ip(request: Request) -> str:
    """获取客户端真实 IP 地址

    优先从 X-Forwarded-For 或 X-Real-IP 头获取(适配反向代理)
    否则使用直连 IP

    Args:
        request: FastAPI Request 对象

    Returns:
        客户端 IP 地址字符串
    """
    # 检查反向代理头
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        # X-Forwarded-For 可能包含多个 IP,取第一个
        return forwarded.split(",")[0].strip()

    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip.strip()

    # 使用直连 IP
    if request.client:
        return request.client.host

    return "unknown"
