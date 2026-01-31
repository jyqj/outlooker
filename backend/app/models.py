#!/usr/bin/env python3
"""
数据模型定义
Pydantic模型用于API请求和响应
"""


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
    accounts: list[ImportAccountData]
    merge_mode: str = "update"  # "update": 更新现有账户, "skip": 跳过重复账户, "replace": 替换所有数据

class ParsedImportRequest(BaseModel):
    """解析后的导入请求模型（包含解析统计信息）"""
    accounts: list[ImportAccountData]
    parsed_count: int
    error_count: int
    errors: list[str]
    merge_mode: str = "update"

class ImportResult(BaseModel):
    """导入结果模型"""
    success: bool
    total_count: int
    added_count: int
    updated_count: int
    skipped_count: int
    error_count: int
    details: list[dict[str, str]]  # 详细信息
    message: str

class AdminLoginRequest(BaseModel):
    """管理员登录请求"""
    username: str
    password: str

class AdminProfile(BaseModel):
    """管理员公开信息"""
    id: int
    username: str
    role: str = "admin"
    is_active: bool = True


class AdminLoginResponse(BaseModel):
    """管理员登录响应"""
    access_token: str
    refresh_token: str | None = None
    token_type: str = "bearer"
    expires_in: int  # 秒数
    refresh_expires_in: int
    user: AdminProfile


class TokenRefreshRequest(BaseModel):
    """刷新令牌请求"""
    refresh_token: str | None = None


class LogoutRequest(BaseModel):
    """登出请求"""
    refresh_token: str | None = None

class TempAccountRequest(BaseModel):
    """临时账户请求"""
    email: EmailStr
    password: str = ""
    client_id: str = ""
    refresh_token: str
    top: int = 5
    folder: str | None = None
    page: int = 1
    page_size: int = 5
    search: str | None = None

class SystemConfigRequest(BaseModel):
    """系统配置请求"""
    email_limit: int = 5

class AccountTagRequest(BaseModel):
    """账户标签请求"""
    email: EmailStr
    tags: list[str] = []

class TestEmailRequest(BaseModel):
    """测试邮件请求模型"""
    email: EmailStr
    password: str = ""
    client_id: str = ""
    refresh_token: str = ""

class ParseImportTextRequest(BaseModel):
    """解析导入文本请求模型"""
    text: str


class PickAccountRequest(BaseModel):
    """随机取号请求模型"""
    tag: str  # 要打的标签
    exclude_tags: list[str] = []  # 排除有这些标签的账户
    return_credentials: bool = False  # 是否返回凭证信息


# ============================================================================
# 响应模型
# ============================================================================

class PaginationInfo(BaseModel):
    """分页信息"""
    page: int
    pageSize: int  # 使用 camelCase 以匹配前端
    total: int
    totalPages: int


class PaginatedResponse(BaseModel):
    """分页响应模型"""
    items: list[dict]
    pagination: PaginationInfo


def create_paginated_response(
    items: list[dict],
    total: int,
    page: int,
    page_size: int,
) -> dict:
    """创建统一的分页响应数据结构"""
    import math
    total_pages = math.ceil(total / page_size) if page_size > 0 else 0
    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "pagination": {
            "page": page,
            "pageSize": page_size,  # camelCase for frontend compatibility
            "total": total,
            "totalPages": total_pages,
        }
    }


class ApiResponse(BaseModel):
    success: bool
    message: str = ""
    data: dict | list | str | None = None
    error_code: str | None = None

class EmailMessage(BaseModel):
    """邮件消息模型"""
    model_config = {"populate_by_name": True}

    id: str
    subject: str
    receivedDateTime: str
    sender: dict
    from_: dict | None = None
    body: dict
    bodyPreview: str = ""
    toRecipients: list[dict] | None = None


class TagStatItem(BaseModel):
    """单个标签的统计信息"""
    name: str
    count: int
    percentage: float


class TagStatsResponse(BaseModel):
    """标签统计响应模型"""
    total_accounts: int
    tagged_accounts: int
    untagged_accounts: int
    tags: list[TagStatItem]


class PickAccountResponse(BaseModel):
    """随机取号响应模型"""
    email: str
    tags: list[str]
    password: str | None = None  # 仅当 return_credentials=true 时返回
    refresh_token: str | None = None  # 仅当 return_credentials=true 时返回
    client_id: str | None = None  # 仅当 return_credentials=true 时返回
