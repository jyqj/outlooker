#!/usr/bin/env python3
"""
IMAP邮件客户端模块
处理IMAP连接和邮件获取操作
"""

import asyncio
import imaplib
import logging
import time
from contextlib import asynccontextmanager
from datetime import datetime

from fastapi import HTTPException

from . import imap_parser as _imap_parser
from .auth.oauth import get_access_token, _get_proxy_url
from .core import exceptions as _exceptions
from .db import db_manager
from .utils.proxy import ProxyIMAP4_SSL
from .imap_parser import (
    build_message_dict,
    fetch_and_parse_single_email,
    parse_email_body,
    parse_email_header,
)
from .settings import get_settings

settings = get_settings()
IMAP_SERVER = settings.imap_server
IMAP_PORT = settings.imap_port
INBOX_FOLDER_NAME = settings.inbox_folder_name

logger = logging.getLogger(__name__)

# 兼容旧的 import 路径：tests/外部模块可能从 app.imap_client 导入这些符号
IMAPError = _exceptions.IMAPError
IMAPConnectionError = _exceptions.IMAPConnectionError
IMAPAuthenticationError = _exceptions.IMAPAuthenticationError
decode_header_value = _imap_parser.decode_header_value

# ============================================================================
# IMAP客户端类
# ============================================================================
class IMAPEmailClient:
    """IMAP邮件客户端（按需连接模式）"""

    def __init__(self, email: str, account_info: dict):
        """初始化IMAP邮件客户端
        
        Args:
            email: 邮箱地址
            account_info: 包含refresh_token的账户信息
        """
        self.email = email
        self.refresh_token = account_info['refresh_token']
        self.access_token = ''
        self.expires_at = 0

        # Token管理锁
        self._token_lock = asyncio.Lock()

        logger.debug("IMAPEmailClient初始化 (%s)，采用按需连接策略", email)

    def is_token_expired(self) -> bool:
        """检查access token是否过期或即将过期"""
        buffer_time = settings.imap_buffer_time_seconds
        return datetime.now().timestamp() + buffer_time >= self.expires_at

    async def ensure_token_valid(self):
        """确保token有效（异步版本，带并发控制）"""
        async with self._token_lock:
            if not self.access_token or self.is_token_expired():
                logger.info("%s access token已过期或不存在，需要刷新", self.email)
                await self.refresh_access_token()

    async def refresh_access_token(self) -> None:
        """刷新访问令牌"""
        try:
            logger.info("正在刷新 %s 的访问令牌...", self.email)
            access_token, new_refresh_token = await get_access_token(self.refresh_token)

            if access_token:
                self.access_token = access_token
                self.expires_at = time.time() + settings.imap_token_expire_seconds
                expires_at_str = datetime.fromtimestamp(self.expires_at).strftime('%Y-%m-%d %H:%M:%S')
                logger.info("Token刷新成功（有效期至: %s）", expires_at_str)
                if new_refresh_token and new_refresh_token != self.refresh_token:
                    self.refresh_token = new_refresh_token
                    try:
                        updated = await db_manager.update_account(self.email, refresh_token=new_refresh_token)
                        if updated:
                            logger.info("已将刷新令牌写回数据库: %s", self.email)
                    except Exception as exc:
                        logger.warning("刷新令牌回写失败(%s): %s", self.email, exc)
            else:
                raise HTTPException(status_code=401, detail="Failed to refresh access token")

        except HTTPException:
            raise
        except asyncio.CancelledError:
            raise
        except Exception as e:
            logger.exception("Token刷新失败 %s: %s", self.email, e)
            raise HTTPException(status_code=500, detail="Failed to refresh access token") from e

    async def create_imap_connection(self, mailbox_to_select=INBOX_FOLDER_NAME):
        """创建IMAP连接（按需创建，带超时和重试）"""
        await self.ensure_token_valid()

        max_retries = settings.imap_max_retries
        timeout = settings.imap_operation_timeout

        proxy_url = await _get_proxy_url()
        if proxy_url:
            logger.info("IMAP 将通过代理连接: %s", proxy_url.split("@")[-1])

        for attempt in range(max_retries):
            try:
                if attempt > 0:
                    logger.info("重试连接 IMAP (第%s次)", attempt + 1)

                def _sync_connect():
                    if proxy_url:
                        imap_conn = ProxyIMAP4_SSL(
                            IMAP_SERVER, IMAP_PORT, proxy_url=proxy_url
                        )
                    else:
                        imap_conn = imaplib.IMAP4_SSL(IMAP_SERVER, IMAP_PORT)

                    auth_string = f"user={self.email}\1auth=Bearer {self.access_token}\1\1"
                    typ, data = imap_conn.authenticate('XOAUTH2', lambda x: auth_string.encode('utf-8'))

                    if typ == 'OK':
                        stat_select, data_select = imap_conn.select(mailbox_to_select, readonly=True)
                        if stat_select == 'OK':
                            return imap_conn
                        else:
                            error_msg = data_select[0].decode('utf-8', 'replace') if data_select and data_select[0] else "未知错误"
                            raise Exception(f"选择邮箱 '{mailbox_to_select}' 失败: {error_msg}")
                    else:
                        error_message = data[0].decode('utf-8', 'replace') if data and data[0] else "未知认证错误"
                        raise Exception(f"IMAP XOAUTH2 认证失败: {error_message} (Type: {typ})")

                imap_conn = await asyncio.wait_for(
                    asyncio.to_thread(_sync_connect), timeout=float(timeout)
                )
                logger.info("IMAP连接已建立 → %s", mailbox_to_select)
                return imap_conn

            except TimeoutError:
                logger.error("创建IMAP连接超时 (%s), 第%s次尝试", self.email, attempt + 1)
                if attempt < max_retries - 1:
                    await asyncio.sleep(1)
                    continue
            except Exception as e:
                # 识别认证错误
                if "authentication failed" in str(e).lower() or "authenticate" in str(e).lower():
                     raise IMAPAuthenticationError(f"认证失败: {e}")

                logger.error("创建IMAP连接失败 (%s), 第%s次尝试: %s", self.email, attempt + 1, e)
                if attempt < max_retries - 1:
                    await asyncio.sleep(1)
                    continue

        logger.error("经过%s次尝试，仍无法创建IMAP连接 (%s)", max_retries, self.email)
        raise IMAPConnectionError(f"Failed to connect to IMAP server for {self.email} after {max_retries} retries")

    def close_imap_connection(self, imap_conn):
        """安全关闭IMAP连接"""
        if imap_conn:
            try:
                current_state = getattr(imap_conn, 'state', None)

                try:
                    if current_state == 'SELECTED':
                        imap_conn.close()
                except Exception as e:
                    logger.debug("关闭邮箱时出现预期错误: %s", e)

                try:
                    if current_state != 'LOGOUT':
                        imap_conn.logout()
                except Exception as e:
                    logger.debug("登出时出现预期错误: %s", e)

                logger.info("IMAP连接已关闭")
            except Exception as e:
                logger.debug("关闭IMAP连接时发生预期错误: %s", e)

    @asynccontextmanager
    async def _imap_connection(self, folder_id: str):
        """提供 IMAP 连接的异步上下文管理器，确保始终释放资源"""
        imap_conn = None
        try:
            imap_conn = await self.create_imap_connection(folder_id)
            yield imap_conn
        finally:
            if imap_conn:
                self.close_imap_connection(imap_conn)

    # ========================================================================
    # 邮件解析辅助函数（委托给 imap_parser）
    # ========================================================================

    @staticmethod
    def _parse_email_header(email_message) -> dict:
        return parse_email_header(email_message)

    @staticmethod
    def _parse_email_body(email_message) -> dict:
        return parse_email_body(email_message)

    @staticmethod
    def _build_message_dict(uid_bytes: bytes, header_info: dict, body_info: dict) -> dict:
        return build_message_dict(uid_bytes, header_info, body_info)

    @staticmethod
    def _fetch_and_parse_single_email(imap_conn, uid_bytes: bytes) -> dict | None:
        return fetch_and_parse_single_email(imap_conn, uid_bytes)

    @staticmethod
    def _scan_email_uids(imap_conn, folder_id: str, top: int) -> list[bytes]:
        """扫描并选择邮件UID列表

        Args:
            imap_conn: IMAP连接对象
            folder_id: 文件夹ID
            top: 需要获取的邮件数量

        Returns:
            UID字节列表(已按最新在前排序)
        """
        # 快速扫描邮件UID列表(毫秒级操作)
        scan_start = time.time()
        typ, uid_data = imap_conn.uid('search', None, "ALL")
        if typ != 'OK':
            raise Exception(f"在 '{folder_id}' 中搜索邮件失败 (status: {typ})。")

        if not uid_data[0]:
            return []

        uids = uid_data[0].split()
        scan_time = (time.time() - scan_start) * 1000
        logger.info("扫描完成: 共 %s 封邮件 (耗时: %.0fms)", len(uids), scan_time)

        # 只获取最新的top条邮件
        uids = uids[-top:] if len(uids) > top else uids
        uids.reverse()  # 最新的在前

        return uids

    async def _cache_messages(self, folder_id: str, messages: list[dict]) -> None:
        """批量缓存邮件到数据库

        Args:
            messages: 消息列表
        """
        try:
            for msg in messages:
                msg_id = msg.get('id')
                if not msg_id:
                    continue
                try:
                    await db_manager.cache_email(self.email, msg_id, msg, folder=folder_id)
                except Exception as cache_exc:
                    logger.debug("缓存邮件失败(忽略): %s", cache_exc)
        except Exception as exc:
            logger.debug("批量缓存邮件时发生预期错误: %s", exc)

    async def get_messages_with_content(self, folder_id: str = INBOX_FOLDER_NAME, top: int = 5) -> list[dict]:
        """获取指定文件夹的邮件（一次性获取完整内容，包括正文）

        优化点：
        - 一次性获取邮件的完整内容（头部+正文）
        - 前端可以缓存这些数据，查看详情时无需再次请求
        - 重构后代码结构清晰，易于维护和测试

        Args:
            folder_id: 文件夹ID, 默认为'INBOX'
            top: 获取的邮件数量
        """
        start_time = time.time()
        logger.info("开始获取 %s 的邮件（文件夹: %s, 请求数量: %s）", self.email, folder_id, top)

        try:
            async with self._imap_connection(folder_id) as imap_conn:

                def _sync_get_messages_full():
                    # 1. 扫描邮件UID列表
                    uids = self._scan_email_uids(imap_conn, folder_id, top)

                    if not uids:
                        return []

                    # 2. 获取并解析每封邮件
                    fetch_start = time.time()
                    logger.info("开始获取 %s 封邮件的完整内容（包含正文和附件）...", len(uids))

                    messages = []
                    for uid_bytes in uids:
                        msg = self._fetch_and_parse_single_email(imap_conn, uid_bytes)
                        if msg:
                            messages.append(msg)

                    fetch_time = (time.time() - fetch_start) * 1000
                    avg_time = fetch_time / len(messages) if messages else 0
                    logger.info("内容获取完成: %s 封邮件 (耗时: %.0fms, 平均: %.0fms/封)", len(messages), fetch_time, avg_time)

                    return messages

                # 在线程池中执行同步IMAP操作
                messages = await asyncio.to_thread(_sync_get_messages_full)

                # 将结果写入本地缓存
                await self._cache_messages(folder_id, messages)

            total_time = (time.time() - start_time) * 1000
            logger.info("完成！总耗时: %.0fms | 获取 %s 封完整邮件", total_time, len(messages))
            return messages

        except asyncio.CancelledError:
            logger.warning("获取邮件操作被取消 (%s)", self.email)
            raise
        except IMAPAuthenticationError as e:
            logger.error("认证失败 %s: %s", self.email, e)
            raise HTTPException(status_code=401, detail="邮箱认证失败，请检查账户凭证")
        except IMAPConnectionError as e:
            logger.error("连接失败 %s: %s", self.email, e)
            raise HTTPException(status_code=503, detail="邮箱服务连接失败，请稍后重试")
        except Exception as e:
            logger.error("获取邮件失败 %s: %s", self.email, e)
            raise HTTPException(status_code=500, detail="Failed to retrieve emails")

    async def get_messages_since_uid(
        self,
        folder_id: str = INBOX_FOLDER_NAME,
        since_uid: int = 0,
        max_count: int = 50,
    ) -> list[dict]:
        """增量获取指定 UID 之后的新邮件（包含正文），并写入本地缓存。

        - 仅在缓存已有数据且需要刷新时使用
        - 返回“新邮件列表”（最新在前）；调用方可再从缓存读取组合结果
        """
        try:
            since_uid_int = int(since_uid or 0)
        except (TypeError, ValueError):
            since_uid_int = 0
        if since_uid_int < 0:
            since_uid_int = 0

        try:
            max_count_int = int(max_count or 0)
        except (TypeError, ValueError):
            max_count_int = 0
        max_count_int = max(0, max_count_int)
        if max_count_int == 0:
            return []

        start_time = time.time()
        logger.info(
            "📨 增量刷新 %s (%s) since_uid=%s",
            self.email,
            folder_id,
            since_uid_int,
        )

        try:
            async with self._imap_connection(folder_id) as imap_conn:

                def _sync_fetch_new_messages_full():
                    uid_range = f"{since_uid_int + 1}:*"
                    typ, uid_data = imap_conn.uid("search", None, "UID", uid_range)
                    if typ != "OK":
                        raise Exception(
                            f"在 '{folder_id}' 中搜索新邮件失败 (status: {typ})。"
                        )

                    if not uid_data or not uid_data[0]:
                        return []

                    uids = uid_data[0].split()
                    # 只取最新的 max_count 条
                    if len(uids) > max_count_int:
                        uids = uids[-max_count_int:]

                    messages: list[dict] = []
                    for uid_bytes in reversed(uids):  # 最新在前
                        msg = self._fetch_and_parse_single_email(imap_conn, uid_bytes)
                        if msg:
                            messages.append(msg)
                    return messages

                messages = await asyncio.to_thread(_sync_fetch_new_messages_full)
                await self._cache_messages(folder_id, messages)

            total_time = (time.time() - start_time) * 1000
            logger.info(
                "✅ 增量刷新完成: 新增 %s 封邮件 (耗时: %.0fms)",
                len(messages),
                total_time,
            )
            return messages

        except asyncio.CancelledError:
            logger.warning("增量获取邮件操作被取消 (%s)", self.email)
            raise
        except IMAPAuthenticationError as e:
            logger.error("认证失败 %s: %s", self.email, e)
            raise HTTPException(status_code=401, detail="邮箱认证失败，请检查账户凭证")
        except IMAPConnectionError as e:
            logger.error("连接失败 %s: %s", self.email, e)
            raise HTTPException(status_code=503, detail="邮箱服务连接失败，请稍后重试")
        except Exception as e:
            logger.error("增量获取邮件失败 %s: %s", self.email, e)
            raise HTTPException(status_code=500, detail="Failed to retrieve emails")

    async def cleanup(self):
        """清理资源"""
        logger.debug("IMAPEmailClient清理完成 (%s)", self.email)
