#!/usr/bin/env python3
"""
IMAP 邮件解析工具

从原 IMAPEmailClient 中抽离的纯解析逻辑，便于单元测试与复用：
- decode_header_value: 解码头部字符串
- parse_email_header: 解析邮件头部
- parse_email_body: 解析正文（HTML/纯文本）
- build_message_dict: 组装 API 返回格式
- fetch_and_parse_single_email: 从 IMAP fetch 并解析单封邮件
"""

from __future__ import annotations

import email
import imaplib
import logging
import re
from email import utils as email_utils
from email.errors import MessageError
from email.header import decode_header

from .core.exceptions import IMAPConnectionError

logger = logging.getLogger(__name__)


def decode_header_value(header_value) -> str:
    """解码邮件头部信息"""
    if header_value is None:
        return ""
    decoded_string = ""
    try:
        parts = decode_header(str(header_value))
        for part, charset in parts:
            if isinstance(part, bytes):
                try:
                    decoded_string += part.decode(charset if charset else "utf-8", "replace")
                except LookupError:
                    decoded_string += part.decode("utf-8", "replace")
            else:
                decoded_string += str(part)
    except Exception:
        if isinstance(header_value, str):
            return header_value
        try:
            return str(header_value, "utf-8", "replace") if isinstance(header_value, bytes) else str(header_value)
        except Exception:
            return "[Header Decode Error]"
    return decoded_string


def parse_email_header(email_message) -> dict:
    """解析邮件头部信息"""
    subject = decode_header_value(email_message["Subject"]) or "(No Subject)"
    from_str = decode_header_value(email_message["From"]) or "(Unknown Sender)"
    to_str = decode_header_value(email_message["To"]) or ""
    date_str = email_message["Date"] or "(Unknown Date)"

    from_name = "(Unknown)"
    from_email = ""
    if "<" in from_str and ">" in from_str:
        from_name = from_str.split("<")[0].strip().strip('"')
        from_email = from_str.split("<")[1].split(">")[0].strip()
    else:
        from_email = from_str.strip()
        if "@" in from_email:
            from_name = from_email.split("@")[0]

    try:
        dt_obj = email_utils.parsedate_to_datetime(date_str)
        if dt_obj:
            date_str = dt_obj.strftime("%Y-%m-%d %H:%M:%S")
    except Exception:
        date_str = date_str[:25] if len(date_str) > 25 else date_str

    return {
        "subject": subject,
        "from_name": from_name,
        "from_email": from_email,
        "to_str": to_str,
        "date_str": date_str,
    }


def parse_email_body(email_message) -> dict:
    """解析邮件正文(支持 multipart 和非 multipart)"""
    body_content = ""
    body_type = "text"
    body_preview = ""

    if email_message.is_multipart():
        html_content: str | None = None
        text_content: str | None = None

        for part in email_message.walk():
            content_type = part.get_content_type()
            content_disposition = str(part.get("Content-Disposition"))

            if "attachment" in content_disposition.lower():
                continue

            try:
                charset = part.get_content_charset() or "utf-8"
                payload = part.get_payload(decode=True)
                if payload is None:
                    continue

                if content_type == "text/html" and not html_content:
                    html_content = payload.decode(charset, errors="replace")
                elif content_type == "text/plain" and not text_content:
                    text_content = payload.decode(charset, errors="replace")
            except Exception:
                continue

        if html_content:
            body_content = html_content
            body_type = "html"
            body_preview = re.sub("<[^<]+?>", "", html_content)[:150]
        elif text_content:
            body_content = text_content
            body_type = "text"
            body_preview = text_content[:150]
        else:
            body_content = "[未找到可读的邮件内容]"
            body_preview = "[未找到可读的邮件内容]"
    else:
        try:
            charset = email_message.get_content_charset() or "utf-8"
            payload = email_message.get_payload(decode=True)
            if payload is None:
                raise ValueError("empty payload")
            body_content = payload.decode(charset, errors="replace")

            if "<html" in body_content.lower() or "<body" in body_content.lower():
                body_type = "html"
                body_preview = re.sub("<[^<]+?>", "", body_content)[:150]
            else:
                body_preview = body_content[:150]
        except Exception:
            body_content = "[Failed to decode email body]"
            body_preview = "[Failed to decode email body]"

    if not body_content:
        body_content = "[未找到可读的文本内容]"
        body_preview = "[未找到可读的文本内容]"

    return {
        "body_content": body_content,
        "body_type": body_type,
        "body_preview": body_preview,
    }


def build_message_dict(uid_bytes: bytes, header_info: dict, body_info: dict) -> dict:
    """构建符合 API 格式的消息字典"""
    return {
        "id": uid_bytes.decode("utf-8"),
        "subject": header_info["subject"],
        "receivedDateTime": header_info["date_str"],
        "sender": {"emailAddress": {"address": header_info["from_email"], "name": header_info["from_name"]}},
        "from": {"emailAddress": {"address": header_info["from_email"], "name": header_info["from_name"]}},
        "toRecipients": (
            [{"emailAddress": {"address": header_info["to_str"], "name": header_info["to_str"]}}]
            if header_info["to_str"]
            else []
        ),
        "body": {"content": body_info["body_content"], "contentType": body_info["body_type"]},
        "bodyPreview": body_info["body_preview"],
    }


def fetch_and_parse_single_email(imap_conn, uid_bytes: bytes) -> dict | None:
    """获取并解析单封邮件，失败返回 None"""
    try:
        typ, msg_data = imap_conn.uid("fetch", uid_bytes, "(RFC822)")
        if typ != "OK" or not msg_data or msg_data[0] is None:
            return None

        raw_email_bytes: bytes | None = None
        if isinstance(msg_data[0], tuple) and len(msg_data[0]) == 2:
            raw_email_bytes = msg_data[0][1]

        if not raw_email_bytes:
            return None

        email_message = email.message_from_bytes(raw_email_bytes)
        header_info = parse_email_header(email_message)
        body_info = parse_email_body(email_message)
        return build_message_dict(uid_bytes, header_info, body_info)
    except imaplib.IMAP4.abort as exc:
        logger.error("IMAP 会话中断（UID: %s）: %s", uid_bytes, exc)
        raise IMAPConnectionError(f"IMAP session aborted: {exc}") from exc
    except imaplib.IMAP4.error as exc:
        logger.error("IMAP 操作失败（UID: %s）: %s", uid_bytes, exc)
        raise IMAPConnectionError(f"IMAP fetch failed: {exc}") from exc
    except (MessageError, UnicodeDecodeError, ValueError) as exc:
        logger.warning("解析邮件（UID: %s）失败，跳过: %s", uid_bytes, exc)
    except Exception as exc:
        logger.exception("处理邮件UID %s 时出现未知错误: %s", uid_bytes, exc)
    return None

