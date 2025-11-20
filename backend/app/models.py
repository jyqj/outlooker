#!/usr/bin/env python3
"""
数据模型定义
Pydantic模型用于API请求和响应
"""

from typing import Dict, List, Optional, Union
from pydantic import BaseModel, EmailStr

# ============================================================================
# 请求模型
# ============================================================================

class AccountCredentials(BaseModel):
    email: EmailStr
    password: str = ""
    client_id: str = ""
    refresh_token: str

class ImportAccountData(BaseModel):
    """单个导入账户数据模型"""
    email: str  # 暂时使用str而不EmailStr避免验证问题
    password: str = ""
    client_id: str = ""
    refresh_token: str

class ImportRequest(BaseModel):
    """批量导入请求模型"""
    accounts: List[ImportAccountData]
    merge_mode: str = "update"  # "update": 更新现有账户, "skip": 跳过重复账户, "replace": 替换所有数据

class ParsedImportRequest(BaseModel):
    """解析后的导入请求模型（包含解析统计信息）"""
    accounts: List[ImportAccountData]
    parsed_count: int
    error_count: int
    errors: List[str]
    merge_mode: str = "update"

class ImportResult(BaseModel):
    """导入结果模型"""
    success: bool
    total_count: int
    added_count: int
    updated_count: int
    skipped_count: int
    error_count: int
    details: List[Dict[str, str]]  # 详细信息
    message: str

class AdminTokenRequest(BaseModel):
    """管理令牌验证请求（向后兼容）"""
    token: str

class AdminLoginRequest(BaseModel):
    """管理员登录请求"""
    username: str
    password: str

class AdminLoginResponse(BaseModel):
    """管理员登录响应"""
    access_token: str
    token_type: str = "bearer"
    expires_in: int  # 秒数

class TempAccountRequest(BaseModel):
    """临时账户请求"""
    email: EmailStr
    password: str = ""
    client_id: str = ""
    refresh_token: str
    top: int = 5
    folder: Optional[str] = None
    page: int = 1
    page_size: int = 5
    search: Optional[str] = None

class SystemConfigRequest(BaseModel):
    """系统配置请求"""
    email_limit: int = 5

class AccountTagRequest(BaseModel):
    """账户标签请求"""
    email: EmailStr
    tags: List[str] = []

class TestEmailRequest(BaseModel):
    """测试邮件请求模型"""
    email: EmailStr
    password: str = ""
    client_id: str = ""
    refresh_token: str = ""

class ParseImportTextRequest(BaseModel):
    """解析导入文本请求模型"""
    text: str

# ============================================================================
# 响应模型
# ============================================================================

class ApiResponse(BaseModel):
    success: bool
    message: str = ""
    data: Optional[Union[Dict, List, str]] = None

class EmailMessage(BaseModel):
    """邮件消息模型"""
    model_config = {"populate_by_name": True}
    
    id: str
    subject: str
    receivedDateTime: str
    sender: Dict
    from_: Optional[Dict] = None
    body: Dict
    bodyPreview: str = ""
    toRecipients: Optional[List[Dict]] = None
