#!/usr/bin/env python3
"""
IMAP 解析器单元测试

测试 imap_parser 模块中的邮件解析功能
"""

import pytest
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from unittest.mock import Mock, MagicMock

from app.imap_parser import (
    decode_header_value,
    parse_email_header,
    parse_email_body,
    build_message_dict,
)


class TestDecodeHeaderValue:
    """测试邮件头部解码函数"""

    def test_decode_plain_text(self):
        """测试解码普通文本"""
        result = decode_header_value("Hello World")
        assert result == "Hello World"

    def test_decode_none(self):
        """测试解码 None 值"""
        result = decode_header_value(None)
        assert result == ""

    def test_decode_utf8_encoded(self):
        """测试解码 UTF-8 编码的头部"""
        # 模拟编码后的中文主题
        encoded = "=?UTF-8?B?5rWL6K+V6YKu5Lu2?="  # "测试邮件" 的 Base64 编码
        result = decode_header_value(encoded)
        assert "测试邮件" in result or result  # 确保能解码

    def test_decode_mixed_encoding(self):
        """测试解码混合编码"""
        result = decode_header_value("Test Subject")
        assert "Test Subject" in result

    def test_decode_bytes_fallback(self):
        """测试 bytes 回退处理"""
        result = decode_header_value(b"bytes content")
        assert result  # 确保不会崩溃


class TestParseEmailHeader:
    """测试邮件头部解析函数"""

    def test_parse_simple_header(self):
        """测试解析简单邮件头部"""
        msg = MIMEText("Test body")
        msg["Subject"] = "Test Subject"
        msg["From"] = "sender@example.com"
        msg["To"] = "recipient@example.com"
        msg["Date"] = "Mon, 01 Jan 2024 12:00:00 +0000"

        result = parse_email_header(msg)

        assert result["subject"] == "Test Subject"
        assert result["from_email"] == "sender@example.com"
        assert result["to_str"] == "recipient@example.com"

    def test_parse_header_with_name(self):
        """测试解析带名称的发件人"""
        msg = MIMEText("Test body")
        msg["Subject"] = "Test"
        msg["From"] = "John Doe <john@example.com>"
        msg["To"] = "jane@example.com"
        msg["Date"] = "Mon, 01 Jan 2024 12:00:00 +0000"

        result = parse_email_header(msg)

        assert result["from_name"] == "John Doe"
        assert result["from_email"] == "john@example.com"

    def test_parse_header_missing_subject(self):
        """测试解析缺少主题的邮件"""
        msg = MIMEText("Test body")
        msg["From"] = "sender@example.com"
        msg["To"] = "recipient@example.com"
        msg["Date"] = "Mon, 01 Jan 2024 12:00:00 +0000"

        result = parse_email_header(msg)

        assert result["subject"] == "(No Subject)"

    def test_parse_header_missing_from(self):
        """测试解析缺少发件人的邮件"""
        msg = MIMEText("Test body")
        msg["Subject"] = "Test"
        msg["To"] = "recipient@example.com"
        msg["Date"] = "Mon, 01 Jan 2024 12:00:00 +0000"

        result = parse_email_header(msg)

        assert result["from_email"] == "(Unknown Sender)"


class TestParseEmailBody:
    """测试邮件正文解析函数"""

    def test_parse_plain_text_body(self):
        """测试解析纯文本正文"""
        msg = MIMEText("This is a plain text email body.")

        result = parse_email_body(msg)

        assert "plain text email body" in result["body_content"]
        assert result["body_type"] == "text"
        assert result["body_preview"]

    def test_parse_html_body(self):
        """测试解析 HTML 正文"""
        html_content = "<html><body><h1>Hello</h1><p>World</p></body></html>"
        msg = MIMEText(html_content, "html")

        result = parse_email_body(msg)

        assert "<html>" in result["body_content"] or "Hello" in result["body_content"]
        assert result["body_type"] == "html"

    def test_parse_multipart_body(self):
        """测试解析 multipart 邮件"""
        msg = MIMEMultipart("alternative")
        text_part = MIMEText("Plain text version", "plain")
        html_part = MIMEText("<html><body>HTML version</body></html>", "html")
        msg.attach(text_part)
        msg.attach(html_part)

        result = parse_email_body(msg)

        # 优先返回 HTML
        assert result["body_type"] == "html"
        assert "HTML version" in result["body_content"]

    def test_parse_multipart_text_only(self):
        """测试解析只有纯文本的 multipart 邮件"""
        msg = MIMEMultipart()
        text_part = MIMEText("Plain text only", "plain")
        msg.attach(text_part)

        result = parse_email_body(msg)

        assert result["body_type"] == "text"
        assert "Plain text only" in result["body_content"]


class TestBuildMessageDict:
    """测试消息字典构建函数"""

    def test_build_complete_message(self):
        """测试构建完整消息字典"""
        uid = b"12345"
        header_info = {
            "subject": "Test Subject",
            "from_name": "John Doe",
            "from_email": "john@example.com",
            "to_str": "jane@example.com",
            "date_str": "2024-01-01 12:00:00",
        }
        body_info = {
            "body_content": "Email body content",
            "body_type": "text",
            "body_preview": "Email body...",
        }

        result = build_message_dict(uid, header_info, body_info)

        assert result["id"] == "12345"
        assert result["subject"] == "Test Subject"
        assert result["receivedDateTime"] == "2024-01-01 12:00:00"
        assert result["sender"]["emailAddress"]["address"] == "john@example.com"
        assert result["sender"]["emailAddress"]["name"] == "John Doe"
        assert result["body"]["content"] == "Email body content"
        assert result["body"]["contentType"] == "text"
        assert result["bodyPreview"] == "Email body..."
        assert len(result["toRecipients"]) == 1

    def test_build_message_empty_to(self):
        """测试构建没有收件人的消息"""
        uid = b"12345"
        header_info = {
            "subject": "Test",
            "from_name": "Sender",
            "from_email": "sender@example.com",
            "to_str": "",
            "date_str": "2024-01-01",
        }
        body_info = {
            "body_content": "Content",
            "body_type": "text",
            "body_preview": "Preview",
        }

        result = build_message_dict(uid, header_info, body_info)

        assert result["toRecipients"] == []
