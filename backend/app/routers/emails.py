from fastapi import APIRouter, HTTPException
from typing import List, Optional, Tuple

from ..models import ApiResponse, TempAccountRequest, TestEmailRequest
from ..config import logger, DEFAULT_EMAIL_LIMIT, INBOX_FOLDER_NAME, MAX_EMAIL_LIMIT
from ..services import email_manager, get_system_config_value
from ..imap_client import IMAPEmailClient

router = APIRouter(tags=["邮件查看"])

def _filter_and_paginate_messages(
    messages: List[dict], page: int, page_size: int, search: Optional[str]
) -> Tuple[List[dict], int]:
    """根据搜索条件过滤邮件并分页。"""
    filtered = messages
    if search:
        kw = search.lower()
        filtered = []
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

    total = len(filtered)
    start = (page - 1) * page_size
    end = start + page_size
    return filtered[start:end], total


@router.get("/api/messages")
async def get_messages(
    email: str,
    page: int = 1,
    page_size: int = 5,
    folder: Optional[str] = None,
    search: Optional[str] = None,
) -> ApiResponse:
    """获取邮件列表（包含完整内容）"""
    email = email.strip()

    if not email:
        return ApiResponse(success=False, message="请提供邮箱地址")

    page = max(1, page)
    page_size = max(1, min(page_size, MAX_EMAIL_LIMIT))
    system_limit = await get_system_config_value("email_limit", DEFAULT_EMAIL_LIMIT)
    requested = page * page_size
    top = min(MAX_EMAIL_LIMIT, max(system_limit, requested))

    try:
        messages = await email_manager.get_messages(email, top, folder)
        items, total = _filter_and_paginate_messages(messages, page, page_size, search)
        return ApiResponse(
            success=True,
            data={
                "items": items,
                "page": page,
                "page_size": page_size,
                "total": total,
                "folder": folder or INBOX_FOLDER_NAME,
            },
        )
    except HTTPException as e:
        return ApiResponse(success=False, message=e.detail)
    except Exception as e:
        logger.exception(f"获取邮件列表失败: {e}")
        return ApiResponse(success=False, message="获取邮件列表失败")

@router.post("/api/temp-messages")
async def get_temp_messages(request: TempAccountRequest) -> ApiResponse:
    """使用临时账户获取邮件列表（包含完整内容）"""
    try:
        account_info = {
            "password": request.password,
            "refresh_token": request.refresh_token,
        }

        temp_client = IMAPEmailClient(request.email, account_info)

        try:
            limit = max(request.top or 1, request.page * request.page_size)
            limit = min(limit, MAX_EMAIL_LIMIT)
            messages = await temp_client.get_messages_with_content(
                folder_id=request.folder or INBOX_FOLDER_NAME,
                top=limit,
            )
            items, total = _filter_and_paginate_messages(
                messages, max(1, request.page), max(1, request.page_size), request.search
            )
            return ApiResponse(
                success=True,
                data={
                    "items": items,
                    "page": request.page,
                    "page_size": request.page_size,
                    "total": total,
                    "folder": request.folder or INBOX_FOLDER_NAME,
                },
            )
        finally:
            await temp_client.cleanup()

    except HTTPException as e:
        return ApiResponse(success=False, message=e.detail)
    except Exception as e:
        logger.exception(f"临时账户获取邮件失败: {e}")
        return ApiResponse(success=False, message=f"获取邮件失败: {str(e)}")

@router.post("/api/test-email")
async def test_email_connection(request: TestEmailRequest) -> ApiResponse:
    """测试邮件连接

    使用 Pydantic 模型验证请求数据

    请求体:
    {
        "email": "user@example.com",
        "password": "optional",
        "client_id": "optional",
        "refresh_token": "optional"
    }
    """
    try:
        email = request.email.strip()
        if not email:
            return ApiResponse(success=False, message="请提供邮箱地址")

        if request.refresh_token:
            # 临时账户测试
            account_info = {
                'password': request.password,
                'refresh_token': request.refresh_token
            }
            
            temp_client = IMAPEmailClient(email, account_info)
            try:
                messages = await temp_client.get_messages_with_content(top=1)
                if messages:
                    latest_message = messages[0]
                    return ApiResponse(
                        success=True, 
                        data=latest_message,
                        message="测试成功，获取到最新邮件"
                    )
                else:
                    return ApiResponse(
                        success=True, 
                        data=None,
                        message="测试成功，但该邮箱暂无邮件"
                    )
            finally:
                await temp_client.cleanup()
        else:
            # 配置文件中的账户测试
            messages = await email_manager.get_messages(email, 1)
            if messages:
                latest_message = messages[0]
                return ApiResponse(
                    success=True, 
                    data=latest_message,
                    message="测试成功，获取到最新邮件"
                )
            else:
                return ApiResponse(
                    success=True, 
                    data=None,
                    message="测试成功，但该邮箱暂无邮件"
                )
                
    except HTTPException as e:
        return ApiResponse(success=False, message=e.detail)
    except Exception as e:
        logger.exception(f"测试邮件连接失败: {e}")
        return ApiResponse(success=False, message=f"测试失败: {str(e)}")
