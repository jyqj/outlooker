#!/usr/bin/env python3
"""
测试辅助工具模块

提供可复用的测试数据生成和辅助函数
"""

from typing import Dict, Any, List, Optional
from datetime import datetime
import uuid


def create_test_account(
    email: Optional[str] = None,
    password: str = "test_password",
    client_id: str = "test_client_id",
    refresh_token: Optional[str] = None,
    **overrides: Any
) -> Dict[str, Any]:
    """创建测试账户数据
    
    Args:
        email: 邮箱地址，默认生成随机邮箱
        password: 密码
        client_id: 客户端 ID
        refresh_token: 刷新令牌，默认生成随机值
        **overrides: 覆盖其他字段
        
    Returns:
        账户数据字典
    """
    if email is None:
        email = f"test_{uuid.uuid4().hex[:8]}@example.com"
    if refresh_token is None:
        refresh_token = f"refresh_token_{uuid.uuid4().hex}"
    
    return {
        "email": email,
        "password": password,
        "client_id": client_id,
        "refresh_token": refresh_token,
        **overrides
    }


def create_test_email_message(
    message_id: Optional[str] = None,
    subject: str = "Test Subject",
    sender_email: str = "sender@example.com",
    sender_name: str = "Test Sender",
    body_content: str = "Test body content",
    body_type: str = "text",
    received_datetime: Optional[str] = None,
    **overrides: Any
) -> Dict[str, Any]:
    """创建测试邮件消息数据
    
    Args:
        message_id: 消息 ID，默认生成随机值
        subject: 邮件主题
        sender_email: 发件人邮箱
        sender_name: 发件人名称
        body_content: 邮件正文
        body_type: 正文类型（text/html）
        received_datetime: 接收时间，默认当前时间
        **overrides: 覆盖其他字段
        
    Returns:
        邮件消息数据字典
    """
    if message_id is None:
        message_id = str(uuid.uuid4())
    if received_datetime is None:
        received_datetime = datetime.utcnow().isoformat() + "Z"
    
    return {
        "id": message_id,
        "subject": subject,
        "sender": {
            "emailAddress": {
                "name": sender_name,
                "address": sender_email
            }
        },
        "receivedDateTime": received_datetime,
        "body": {
            "content": body_content,
            "contentType": body_type
        },
        "bodyPreview": body_content[:100] if len(body_content) > 100 else body_content,
        **overrides
    }


def create_test_tag_list(count: int = 3, prefix: str = "tag") -> List[str]:
    """创建测试标签列表
    
    Args:
        count: 标签数量
        prefix: 标签前缀
        
    Returns:
        标签列表
    """
    return [f"{prefix}_{i}" for i in range(1, count + 1)]


def create_test_import_data(
    count: int = 3,
    merge_mode: str = "update"
) -> Dict[str, Any]:
    """创建测试导入数据
    
    Args:
        count: 账户数量
        merge_mode: 合并模式（update/skip/replace）
        
    Returns:
        导入请求数据
    """
    return {
        "accounts": [create_test_account() for _ in range(count)],
        "merge_mode": merge_mode
    }


class MockIMAPClient:
    """模拟 IMAP 客户端用于测试"""
    
    def __init__(self, messages: Optional[List[Dict]] = None):
        self.messages = messages or []
        self.connected = False
        self.selected_folder = None
    
    async def get_messages_with_content(
        self,
        folder_id: str = "INBOX",
        top: int = 5
    ) -> List[Dict]:
        """模拟获取邮件"""
        return self.messages[:top]
    
    async def cleanup(self) -> None:
        """模拟清理"""
        self.connected = False
        self.selected_folder = None


# 常用测试数据
SAMPLE_VERIFICATION_CODE_EMAIL = create_test_email_message(
    subject="Your verification code",
    body_content="Your verification code is: 123456. This code expires in 10 minutes.",
)

SAMPLE_ACCOUNTS = [
    create_test_account(email=f"user{i}@example.com")
    for i in range(1, 4)
]
