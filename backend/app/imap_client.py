#!/usr/bin/env python3
"""
IMAP邮件客户端模块
处理IMAP连接和邮件获取操作
"""

import asyncio
import imaplib
import email
import logging
import time
import re
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Dict, List, Optional
from email.header import decode_header
from email.errors import MessageError
from email import utils as email_utils
from fastapi import HTTPException

from .config import IMAP_SERVER, IMAP_PORT, INBOX_FOLDER_NAME
from .auth import get_access_token
from .database import db_manager

logger = logging.getLogger(__name__)

# ============================================================================
# 辅助函数
# ============================================================================

def decode_header_value(header_value):
    """解码邮件头部信息"""
    if header_value is None:
        return ""
    decoded_string = ""
    try:
        parts = decode_header(str(header_value))
        for part, charset in parts:
            if isinstance(part, bytes):
                try:
                    decoded_string += part.decode(charset if charset else 'utf-8', 'replace')
                except LookupError:
                    decoded_string += part.decode('utf-8', 'replace')
            else:
                decoded_string += str(part)
    except Exception:
        if isinstance(header_value, str):
            return header_value
        try:
            return str(header_value, 'utf-8', 'replace') if isinstance(header_value, bytes) else str(header_value)
        except Exception:
            return "[Header Decode Error]"
    return decoded_string



# ============================================================================
# IMAP客户端类
# ============================================================================

class IMAPError(Exception):
    """IMAP 操作基础异常"""
    pass

class IMAPConnectionError(IMAPError):
    """IMAP 连接失败"""
    pass

class IMAPAuthenticationError(IMAPError):
    """IMAP 认证失败"""
    pass

class IMAPEmailClient:
    """IMAP邮件客户端（按需连接模式）"""
    
    def __init__(self, email: str, account_info: Dict):
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
        
        logger.debug(f"IMAPEmailClient初始化 ({email})，采用按需连接策略")
    
    def is_token_expired(self) -> bool:
        """检查access token是否过期或即将过期"""
        buffer_time = 300  # 5分钟缓冲时间
        return datetime.now().timestamp() + buffer_time >= self.expires_at
    
    async def ensure_token_valid(self):
        """确保token有效（异步版本，带并发控制）"""
        async with self._token_lock:
            if not self.access_token or self.is_token_expired():
                logger.info(f"{self.email} access token已过期或不存在，需要刷新")
                await self.refresh_access_token()
    
    async def refresh_access_token(self) -> None:
        """刷新访问令牌"""
        try:
            logger.info(f"🔑 正在刷新 {self.email} 的访问令牌...")
            access_token = await get_access_token(self.refresh_token)
            
            if access_token:
                self.access_token = access_token
                self.expires_at = time.time() + 3600  # 默认1小时过期
                expires_at_str = datetime.fromtimestamp(self.expires_at).strftime('%Y-%m-%d %H:%M:%S')
                logger.info(f"✓ Token刷新成功（有效期至: {expires_at_str}）")
            else:
                raise HTTPException(status_code=401, detail="Failed to refresh access token")
                
        except HTTPException:
            raise
        except asyncio.CancelledError:
            raise
        except Exception as e:
            logger.exception(f"✗ Token刷新失败 {self.email}: {e}")
            raise HTTPException(status_code=500, detail="Failed to refresh access token") from e
    
    async def create_imap_connection(self, mailbox_to_select=INBOX_FOLDER_NAME):
        """创建IMAP连接（按需创建，带超时和重试）"""
        await self.ensure_token_valid()
        
        max_retries = 3
        for attempt in range(max_retries):
            try:
                if attempt > 0:
                    logger.info(f"🔄 重试连接 IMAP (第{attempt+1}次)")
                
                def _sync_connect():
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
                
                # 在线程池中执行，带10秒超时
                imap_conn = await asyncio.wait_for(
                    asyncio.to_thread(_sync_connect), timeout=10.0
                )
                logger.info(f"🔌 IMAP连接已建立 → {mailbox_to_select}")
                return imap_conn
                
            except asyncio.TimeoutError:
                logger.error(f"创建IMAP连接超时 ({self.email}), 第{attempt+1}次尝试")
                if attempt < max_retries - 1:
                    await asyncio.sleep(1)
                    continue
            except Exception as e:
                # 识别认证错误
                if "authentication failed" in str(e).lower() or "authenticate" in str(e).lower():
                     raise IMAPAuthenticationError(f"认证失败: {e}")
                
                logger.error(f"创建IMAP连接失败 ({self.email}), 第{attempt+1}次尝试: {e}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(1)
                    continue
        
        logger.error(f"经过{max_retries}次尝试，仍无法创建IMAP连接 ({self.email})")
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
                    logger.debug(f"关闭邮箱时出现预期错误: {e}")

                try:
                    if current_state != 'LOGOUT':
                        imap_conn.logout()
                except Exception as e:
                    logger.debug(f"登出时出现预期错误: {e}")

                logger.info(f"🔌 IMAP连接已关闭")
            except Exception as e:
                logger.debug(f"关闭IMAP连接时发生预期错误: {e}")

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
    # 邮件解析辅助函数 (重构后提取的独立函数)
    # ========================================================================

    @staticmethod
    def _parse_email_header(email_message) -> Dict:
        """解析邮件头部信息

        Args:
            email_message: email.message.Message 对象

        Returns:
            包含 subject, from_name, from_email, to_str, date_str 的字典
        """
        # 解析基本头部字段
        subject = decode_header_value(email_message['Subject']) or "(No Subject)"
        from_str = decode_header_value(email_message['From']) or "(Unknown Sender)"
        to_str = decode_header_value(email_message['To']) or ""
        date_str = email_message['Date'] or "(Unknown Date)"

        # 解析From字段,提取姓名和邮箱
        from_name = "(Unknown)"
        from_email = ""
        if '<' in from_str and '>' in from_str:
            from_name = from_str.split('<')[0].strip().strip('"')
            from_email = from_str.split('<')[1].split('>')[0].strip()
        else:
            from_email = from_str.strip()
            if '@' in from_email:
                from_name = from_email.split('@')[0]

        # 解析并格式化日期
        try:
            dt_obj = email_utils.parsedate_to_datetime(date_str)
            if dt_obj:
                date_str = dt_obj.strftime('%Y-%m-%d %H:%M:%S')
        except Exception:
            date_str = date_str[:25] if len(date_str) > 25 else date_str

        return {
            'subject': subject,
            'from_name': from_name,
            'from_email': from_email,
            'to_str': to_str,
            'date_str': date_str,
        }

    @staticmethod
    def _parse_email_body(email_message) -> Dict:
        """解析邮件正文(支持multipart和非multipart)

        Args:
            email_message: email.message.Message 对象

        Returns:
            包含 body_content, body_type, body_preview 的字典
        """
        body_content = ""
        body_type = "text"
        body_preview = ""

        if email_message.is_multipart():
            # 处理multipart邮件
            html_content = None
            text_content = None

            for part in email_message.walk():
                content_type = part.get_content_type()
                content_disposition = str(part.get("Content-Disposition"))

                # 跳过附件
                if 'attachment' not in content_disposition.lower():
                    try:
                        charset = part.get_content_charset() or 'utf-8'
                        payload = part.get_payload(decode=True)

                        if content_type == 'text/html' and not html_content:
                            html_content = payload.decode(charset, errors='replace')
                        elif content_type == 'text/plain' and not text_content:
                            text_content = payload.decode(charset, errors='replace')
                    except Exception:
                        continue

            # 优先使用HTML内容
            if html_content:
                body_content = html_content
                body_type = "html"
                # 生成预览文本(移除HTML标签)
                import re
                body_preview = re.sub('<[^<]+?>', '', html_content)[:150]
            elif text_content:
                body_content = text_content
                body_type = "text"
                body_preview = text_content[:150]
            else:
                body_content = "[未找到可读的邮件内容]"
                body_preview = "[未找到可读的邮件内容]"
        else:
            # 处理非multipart邮件
            try:
                charset = email_message.get_content_charset() or 'utf-8'
                payload = email_message.get_payload(decode=True)
                body_content = payload.decode(charset, errors='replace')

                # 检查是否为HTML内容
                if '<html' in body_content.lower() or '<body' in body_content.lower():
                    body_type = "html"
                    import re
                    body_preview = re.sub('<[^<]+?>', '', body_content)[:150]
                else:
                    body_preview = body_content[:150]
            except Exception:
                body_content = "[Failed to decode email body]"
                body_preview = "[Failed to decode email body]"

        if not body_content:
            body_content = "[未找到可读的文本内容]"
            body_preview = "[未找到可读的文本内容]"

        return {
            'body_content': body_content,
            'body_type': body_type,
            'body_preview': body_preview,
        }

    @staticmethod
    def _build_message_dict(uid_bytes: bytes, header_info: Dict, body_info: Dict) -> Dict:
        """构建完整的消息字典

        Args:
            uid_bytes: 邮件UID(字节格式)
            header_info: 头部信息字典
            body_info: 正文信息字典

        Returns:
            符合API格式的消息字典
        """
        return {
            'id': uid_bytes.decode('utf-8'),
            'subject': header_info['subject'],
            'receivedDateTime': header_info['date_str'],
            'sender': {
                'emailAddress': {
                    'address': header_info['from_email'],
                    'name': header_info['from_name']
                }
            },
            'from': {
                'emailAddress': {
                    'address': header_info['from_email'],
                    'name': header_info['from_name']
                }
            },
            'toRecipients': [
                {'emailAddress': {'address': header_info['to_str'], 'name': header_info['to_str']}}
            ] if header_info['to_str'] else [],
            'body': {
                'content': body_info['body_content'],
                'contentType': body_info['body_type']
            },
            'bodyPreview': body_info['body_preview']
        }

    @staticmethod
    def _fetch_and_parse_single_email(imap_conn, uid_bytes: bytes) -> Optional[Dict]:
        """获取并解析单封邮件

        Args:
            imap_conn: IMAP连接对象
            uid_bytes: 邮件UID(字节格式)

        Returns:
            消息字典,失败时返回None
        """
        try:
            # 一次性获取完整邮件内容(RFC822)
            typ, msg_data = imap_conn.uid('fetch', uid_bytes, '(RFC822)')

            if typ == 'OK' and msg_data and msg_data[0] is not None:
                raw_email_bytes = None
                if isinstance(msg_data[0], tuple) and len(msg_data[0]) == 2:
                    raw_email_bytes = msg_data[0][1]

                if raw_email_bytes:
                    email_message = email.message_from_bytes(raw_email_bytes)

                    # 解析头部
                    header_info = IMAPEmailClient._parse_email_header(email_message)

                    # 解析正文
                    body_info = IMAPEmailClient._parse_email_body(email_message)

                    # 构建消息字典
                    message = IMAPEmailClient._build_message_dict(uid_bytes, header_info, body_info)

                    return message
        except imaplib.IMAP4.abort as exc:
            logger.error(f"IMAP 会话中断（UID: {uid_bytes}）: {exc}")
            raise IMAPConnectionError(f"IMAP session aborted: {exc}") from exc
        except imaplib.IMAP4.error as exc:
            logger.error(f"IMAP 操作失败（UID: {uid_bytes}）: {exc}")
            raise IMAPConnectionError(f"IMAP fetch failed: {exc}") from exc
        except (MessageError, UnicodeDecodeError, ValueError) as exc:
            logger.warning(f"解析邮件（UID: {uid_bytes}）失败，跳过: {exc}")
        except Exception as exc:
            logger.exception(f"处理邮件UID {uid_bytes}时出现未知错误: {exc}")

        return None

    @staticmethod
    def _scan_email_uids(imap_conn, folder_id: str, top: int) -> List[bytes]:
        """扫描并选择邮件UID列表

        Args:
            imap_conn: IMAP连接对象
            folder_id: 文件夹ID
            top: 需要获取的邮件数量

        Returns:
            UID字节列表(已按最新在前排序)
        """
        import time

        # 快速扫描邮件UID列表(毫秒级操作)
        scan_start = time.time()
        typ, uid_data = imap_conn.uid('search', None, "ALL")
        if typ != 'OK':
            raise Exception(f"在 '{folder_id}' 中搜索邮件失败 (status: {typ})。")

        if not uid_data[0]:
            return []

        uids = uid_data[0].split()
        scan_time = (time.time() - scan_start) * 1000
        logger.info(f"📋 扫描完成: 共 {len(uids)} 封邮件 (耗时: {scan_time:.0f}ms)")

        # 只获取最新的top条邮件
        uids = uids[-top:] if len(uids) > top else uids
        uids.reverse()  # 最新的在前

        return uids

    async def _cache_messages(self, messages: List[Dict]) -> None:
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
                    await db_manager.cache_email(self.email, msg_id, msg)
                except Exception as cache_exc:
                    logger.debug(f"缓存邮件失败(忽略): {cache_exc}")
        except Exception as exc:
            logger.debug(f"批量缓存邮件时发生预期错误: {exc}")

    async def get_messages_with_content(self, folder_id: str = INBOX_FOLDER_NAME, top: int = 5) -> List[Dict]:
        """获取指定文件夹的邮件（一次性获取完整内容，包括正文）

        优化点：
        - 一次性获取邮件的完整内容（头部+正文）
        - 前端可以缓存这些数据，查看详情时无需再次请求
        - 重构后代码结构清晰，易于维护和测试

        Args:
            folder_id: 文件夹ID, 默认为'INBOX'
            top: 获取的邮件数量
        """
        import time
        start_time = time.time()
        logger.info(f"📧 开始获取 {self.email} 的邮件（文件夹: {folder_id}, 请求数量: {top}）")

        try:
            async with self._imap_connection(folder_id) as imap_conn:

                def _sync_get_messages_full():
                    # 1. 扫描邮件UID列表
                    uids = self._scan_email_uids(imap_conn, folder_id, top)

                    if not uids:
                        return []

                    # 2. 获取并解析每封邮件
                    fetch_start = time.time()
                    logger.info(f"📥 开始获取 {len(uids)} 封邮件的完整内容（包含正文和附件）...")

                    messages = []
                    for uid_bytes in uids:
                        msg = self._fetch_and_parse_single_email(imap_conn, uid_bytes)
                        if msg:
                            messages.append(msg)

                    fetch_time = (time.time() - fetch_start) * 1000
                    logger.info(f"📬 内容获取完成: {len(messages)} 封邮件 (耗时: {fetch_time:.0f}ms, 平均: {fetch_time/len(messages) if messages else 0:.0f}ms/封)")

                    return messages

                # 在线程池中执行同步IMAP操作
                messages = await asyncio.to_thread(_sync_get_messages_full)

                # 将结果写入本地缓存
                await self._cache_messages(messages)

            total_time = (time.time() - start_time) * 1000
            logger.info(f"✅ 完成！总耗时: {total_time:.0f}ms | 获取 {len(messages)} 封完整邮件（已包含正文，前端可缓存）")
            return messages

        except asyncio.CancelledError:
            logger.warning(f"获取邮件操作被取消 ({self.email})")
            raise
        except IMAPAuthenticationError as e:
            logger.error(f"认证失败 {self.email}: {e}")
            raise HTTPException(status_code=401, detail=f"Authentication failed: {str(e)}")
        except IMAPConnectionError as e:
            logger.error(f"连接失败 {self.email}: {e}")
            raise HTTPException(status_code=503, detail=f"Connection failed: {str(e)}")
        except Exception as e:
            logger.error(f"获取邮件失败 {self.email}: {e}")
            raise HTTPException(status_code=500, detail="Failed to retrieve emails")

    async def cleanup(self):
        """清理资源"""
        logger.debug(f"IMAPEmailClient清理完成 ({self.email})")
