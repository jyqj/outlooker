#!/usr/bin/env python3
"""
代理工具函数
解析代理 URL 并提供支持代理的 IMAP4_SSL 子类
"""

from __future__ import annotations

import imaplib
import logging
import ssl
from typing import TYPE_CHECKING
from urllib.parse import urlparse

import socks

if TYPE_CHECKING:
    import socket as _socket_mod

logger = logging.getLogger(__name__)

PROXY_TYPE_MAP: dict[str, int] = {
    "socks5": socks.SOCKS5,
    "socks4": socks.SOCKS4,
    "http": socks.HTTP,
    "https": socks.HTTP,
}


def parse_proxy_url(url: str) -> tuple[int, str, int, str | None, str | None]:
    """解析代理 URL 为 (proxy_type, host, port, username, password)

    支持格式:
        socks5://host:port
        socks5://user:pass@host:port
        http://host:port
    """
    parsed = urlparse(url)
    scheme = (parsed.scheme or "").lower()

    proxy_type = PROXY_TYPE_MAP.get(scheme)
    if proxy_type is None:
        raise ValueError(
            f"不支持的代理协议 '{scheme}'，"
            f"支持: {', '.join(PROXY_TYPE_MAP)}"
        )

    if not parsed.hostname:
        raise ValueError(f"代理 URL 缺少主机名: {url}")
    if not parsed.port:
        raise ValueError(f"代理 URL 缺少端口号: {url}")

    return (
        proxy_type,
        parsed.hostname,
        parsed.port,
        parsed.username,
        parsed.password,
    )


class ProxyIMAP4_SSL(imaplib.IMAP4_SSL):
    """支持 SOCKS5/SOCKS4/HTTP 代理的 IMAP4_SSL

    通过覆写 ``_create_socket`` 在 socket 层注入代理连接，
    其余行为与标准 IMAP4_SSL 完全一致。
    """

    def __init__(
        self,
        host: str = "",
        port: int = 993,
        *,
        proxy_url: str | None = None,
        ssl_context: ssl.SSLContext | None = None,
        timeout: float | None = None,
    ):
        self._proxy_url = proxy_url
        super().__init__(
            host,
            port,
            ssl_context=ssl_context,
            timeout=timeout,
        )

    def _create_socket(self, timeout: float | None = None) -> _socket_mod.socket:
        if not self._proxy_url:
            return super()._create_socket(timeout)

        proxy_type, proxy_host, proxy_port, username, password = parse_proxy_url(
            self._proxy_url
        )

        logger.debug(
            "IMAP 通过代理连接: %s://%s:%s → %s:%s",
            self._proxy_url.split("://")[0],
            proxy_host,
            proxy_port,
            self.host,
            self.port,
        )

        sock = socks.create_connection(
            dest_pair=(self.host, self.port),
            timeout=timeout,
            proxy_type=proxy_type,
            proxy_addr=proxy_host,
            proxy_port=proxy_port,
            proxy_username=username,
            proxy_password=password,
        )
        return sock
