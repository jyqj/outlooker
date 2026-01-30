from fastapi import APIRouter, Depends, HTTPException, Header
from typing import List, Optional, Tuple
import logging

from ..models import ApiResponse, TempAccountRequest, TestEmailRequest, create_paginated_response
from ..settings import get_settings
from ..exceptions import ValidationError, DatabaseError, ResourceNotFoundError

logger = logging.getLogger(__name__)
from ..dependencies import AdminUser, enforce_public_rate_limit, verify_public_token
from ..services import email_manager, get_system_config_value, db_manager
from ..jwt_auth import get_current_admin
from ..imap_client import IMAPEmailClient
from ..utils.pagination import filter_messages_by_search, paginate_items

settings = get_settings()

router = APIRouter(tags=["邮件查看"])

def _filter_and_paginate_messages(
    messages: List[dict], page: int, page_size: int, search: Optional[str]
) -> Tuple[List[dict], int]:
    """根据搜索条件过滤邮件并分页。

    过滤与分页逻辑委托给通用工具函数，避免在路由层重复实现。
    """
    filtered = filter_messages_by_search(messages, search)
    items, total = paginate_items(filtered, page, page_size)
    return items, total


@router.get("/api/messages", dependencies=[Depends(verify_public_token)])
async def get_messages(
    email: str,
    page: int = 1,
    page_size: int = 5,
    folder: Optional[str] = None,
    search: Optional[str] = None,
    refresh: bool = False,
    _: None = Depends(enforce_public_rate_limit),
) -> ApiResponse:
    """获取邮件列表（包含完整内容）"""
    email = email.strip()

    if not email:
        raise ValidationError(message="请提供邮箱地址", field="email")

    page = max(1, page)
    page_size = max(1, min(page_size, settings.max_email_limit))
    system_limit = await get_system_config_value("email_limit", settings.default_email_limit)
    requested = page * page_size
    top = min(settings.max_email_limit, max(system_limit, requested))

    try:
        messages = await email_manager.get_messages(email, top, folder, force_refresh=refresh)
        items, total = _filter_and_paginate_messages(messages, page, page_size, search)
        paginated_data = create_paginated_response(items, total, page, page_size)
        # Add folder info to the response
        paginated_data["folder"] = folder or settings.inbox_folder_name
        return ApiResponse(
            success=True,
            data=paginated_data,
        )
    except (HTTPException, ValidationError, DatabaseError, ResourceNotFoundError):
        raise
    except Exception as e:
        logger.exception(f"获取邮件列表失败: {e}")
        raise DatabaseError(message="获取邮件列表失败")

@router.post("/api/temp-messages", dependencies=[Depends(verify_public_token)])
async def get_temp_messages(request: TempAccountRequest) -> ApiResponse:
    """使用临时账户获取邮件列表（包含完整内容）"""
    account_info = {
        "password": request.password,
        "refresh_token": request.refresh_token,
    }

    temp_client = IMAPEmailClient(request.email, account_info)

    try:
        limit = max(request.top or 1, request.page * request.page_size)
        limit = min(limit, settings.max_email_limit)
        messages = await temp_client.get_messages_with_content(
            folder_id=request.folder or settings.inbox_folder_name,
            top=limit,
        )
        page = max(1, request.page)
        page_size = max(1, request.page_size)
        items, total = _filter_and_paginate_messages(messages, page, page_size, request.search)
        paginated_data = create_paginated_response(items, total, page, page_size)
        paginated_data["folder"] = request.folder or settings.inbox_folder_name
        return ApiResponse(
            success=True,
            data=paginated_data,
        )
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("临时账户获取邮件失败: %s", exc)
        return ApiResponse(
            success=False,
            message="获取邮件失败",
            error_code="TEMP_MESSAGES_FAILED",
        )
    finally:
        await temp_client.cleanup()

@router.post("/api/test-email", dependencies=[Depends(verify_public_token)])
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
            raise ValidationError(message="请提供邮箱地址", field="email")

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
            messages = await email_manager.get_messages(email, top=1, folder=None, force_refresh=True)
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
                
    except (HTTPException, ValidationError):
        raise
    except Exception as e:
        logger.exception(f"测试邮件连接失败: {e}")
        raise DatabaseError(message="测试邮件连接失败")


@router.post(
    "/api/email/{email_account}/{message_id}/read",
    tags=["邮件管理"],
    deprecated=True,
)
async def mark_email_read(
    email_account: str,
    message_id: str,
    admin: AdminUser,
) -> ApiResponse:
    """标记邮件为已读（需要管理员认证）"""
    try:
        success = await db_manager.mark_email_as_read(email_account, message_id)
        if success:
            return ApiResponse(success=True, message="邮件已标记为已读")
        raise ResourceNotFoundError(message="邮件不存在或标记失败", resource_type="email", resource_id=message_id)
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"标记邮件已读失败: {e}")
        raise DatabaseError(message="标记邮件已读失败")


@router.delete("/api/email/{email_account}/{message_id}", tags=["邮件管理"])
async def delete_email(
    email_account: str,
    message_id: str,
    admin: AdminUser,
) -> ApiResponse:
    """删除缓存中的邮件（需要管理员认证）"""
    try:
        success = await db_manager.delete_cached_email(email_account, message_id)
        if success:
            return ApiResponse(success=True, message="邮件已删除")
        raise ResourceNotFoundError(message="邮件不存在或删除失败", resource_type="email", resource_id=message_id)
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"删除邮件失败: {e}")
        raise DatabaseError(message="删除邮件失败")
