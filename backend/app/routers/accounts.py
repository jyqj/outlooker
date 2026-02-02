import logging
from datetime import datetime

from fastapi import APIRouter, HTTPException
from fastapi.responses import PlainTextResponse

from ..dependencies import AdminUser
from ..models import (
    AccountCredentials,
    AccountTagRequest,
    ApiResponse,
    ImportRequest,
    ParseImportTextRequest,
    create_paginated_response,
)
from ..settings import get_settings

logger = logging.getLogger(__name__)
from ..core.decorators import handle_exceptions
from ..core.exceptions import DatabaseError, DuplicateEntryError, ResourceNotFoundError, ValidationError
from ..services import db_manager, email_manager, imap_pool, load_accounts_config, merge_accounts_data_to_db, parse_account_line
from ..utils.pagination import paginate_items
from ..utils.validation import validate_tags

settings = get_settings()

router = APIRouter(tags=["账户管理"])
DEFAULT_ACCOUNT_PAGE_SIZE = 10
MAX_ACCOUNT_PAGE_SIZE = 100


def _mask_secret(value: str) -> str:
    if not value:
        return ""
    plain = value
    if len(plain) <= 4:
        return "*" * len(plain)
    return f"{plain[:2]}***{plain[-2:]}"

@router.get("/api/accounts")
@handle_exceptions("获取账户列表")
async def get_accounts(admin: AdminUser) -> ApiResponse:
    """获取所有账户列表（需要管理员认证）"""
    accounts = await load_accounts_config()
    account_list = [
        {
            "email": email,
            # 来自数据库的账户会包含使用状态字段；文件来源则默认为未使用
            "is_used": bool(info.get("is_used")),
            "last_used_at": info.get("last_used_at"),
        }
        for email, info in accounts.items()
    ]
    return ApiResponse(success=True, data=account_list, message=f"共 {len(account_list)} 个账户")

@router.get("/api/accounts/paged")
@handle_exceptions("分页获取账户列表")
async def get_accounts_paged(
    admin: AdminUser,
    q: str | None = None,
    page: int = 1,
    page_size: int = DEFAULT_ACCOUNT_PAGE_SIZE,
) -> ApiResponse:
    """分页与搜索账户列表（需要管理员认证）"""
    accounts_dict = await load_accounts_config()
    emails = sorted(accounts_dict.keys())

    if q:
        q_lower = q.strip().lower()
        emails = [e for e in emails if q_lower in e.lower()]

    # 统一使用通用分页工具，保持逻辑一致性
    items_page, total = paginate_items(
        emails,
        max(1, page),
        max(1, min(MAX_ACCOUNT_PAGE_SIZE, page_size)),
    )

    # 为每个账户附加使用状态，便于前端展示“已使用/未使用”
    items = []
    for e in items_page:
        info = accounts_dict.get(e, {}) or {}
        items.append(
            {
                "email": e,
                "is_used": bool(info.get("is_used")),
                "last_used_at": info.get("last_used_at"),
            }
        )

    return ApiResponse(
        success=True,
        data=create_paginated_response(items, total, page, page_size),
        message=f"共 {total} 个账户"
    )

@router.get("/api/accounts/tags", tags=["标签管理"])
@handle_exceptions("获取账户标签")
async def get_accounts_tags(admin: AdminUser) -> ApiResponse:
    """获取所有标签和账户-标签映射（需要管理员认证）"""
    tags = await db_manager.get_all_tags()
    accounts_map = await db_manager.get_accounts_with_tags()
    return ApiResponse(success=True, data={"tags": tags, "accounts": accounts_map})


@router.get("/api/accounts/tags/stats", tags=["标签管理"])
@handle_exceptions("获取标签统计")
async def get_tag_statistics(admin: AdminUser) -> ApiResponse:
    """获取标签使用统计（需要管理员认证）
    
    返回：
    - total_accounts: 总账户数
    - tagged_accounts: 有标签的账户数
    - untagged_accounts: 无标签的账户数
    - tags: 标签列表，每个包含 name, count, percentage
    """
    stats = await db_manager.get_tag_statistics()
    return ApiResponse(success=True, data=stats)


@router.post("/api/accounts/pick", tags=["标签管理"])
@handle_exceptions("随机取号")
async def pick_random_account(
    admin: AdminUser,
    request: dict[str, str | list[str] | bool],
) -> ApiResponse:
    """随机取号：获取一个没有指定标签的账户并自动打标签
    
    请求体:
    {
        "tag": "注册-Apple",           // 必填：要打的标签
        "exclude_tags": ["黑名单"],    // 可选：排除有这些标签的账户
        "return_credentials": false    // 可选：是否返回凭证信息
    }
    
    返回:
    {
        "success": true,
        "data": {
            "email": "user@example.com",
            "tags": ["注册-Apple"],
            "password": "***",           // 仅当 return_credentials=true
            "refresh_token": "***"       // 仅当 return_credentials=true
        }
    }
    """
    # 解析请求参数
    tag = request.get("tag")
    if not tag or not isinstance(tag, str) or not tag.strip():
        raise ValidationError(message="请提供要打的标签", field="tag")

    tag = tag.strip()
    validate_tags([tag])  # 校验标签格式

    exclude_tags_raw = request.get("exclude_tags", [])
    exclude_tags: list[str] = []
    if isinstance(exclude_tags_raw, list):
        exclude_tags = [str(t).strip() for t in exclude_tags_raw if str(t).strip()]
    elif isinstance(exclude_tags_raw, str) and exclude_tags_raw.strip():
        exclude_tags = [exclude_tags_raw.strip()]

    if exclude_tags:
        validate_tags(exclude_tags)  # 校验排除标签格式

    return_credentials = bool(request.get("return_credentials", False))

    # 随机获取一个符合条件的账户
    account = await db_manager.get_random_account_without_tag(tag, exclude_tags)

    if not account:
        raise ResourceNotFoundError(
            message=f"没有找到可用的账户（不含标签 '{tag}'）",
            resource_type="account"
        )

    email = account["email"]
    current_tags = account.get("tags", [])

    # 为账户添加标签
    new_tags = list(set(current_tags + [tag]))
    ok = await db_manager.set_account_tags(email, new_tags)
    if not ok:
        raise DatabaseError(message="标记账户失败")

    # 构建响应
    response_data = {
        "email": email,
        "tags": new_tags,
    }

    if return_credentials:
        response_data["password"] = account.get("password", "")
        response_data["refresh_token"] = account.get("refresh_token", "")
        response_data["client_id"] = account.get("client_id", "")

    logger.info(f"随机取号成功: {email}, 标签: {tag}")

    return ApiResponse(
        success=True,
        message=f"成功获取账户并标记为 '{tag}'",
        data=response_data
    )

@router.get("/api/accounts/{email}/tags", tags=["标签管理"])
@handle_exceptions("获取账户标签")
async def get_account_tags(email: str, admin: AdminUser) -> ApiResponse:
    """获取指定账户的标签（需要管理员认证）"""
    tags = await db_manager.get_account_tags(email)
    return ApiResponse(success=True, data={"email": email, "tags": tags})

@router.post("/api/accounts/{email}/tags", tags=["标签管理"])
@handle_exceptions("保存账户标签")
async def set_account_tags(
    email: str,
    admin: AdminUser,
    request: AccountTagRequest,
) -> ApiResponse:
    """设置指定账户的标签（需要管理员认证）"""
    # 保护：路径中的邮箱与请求体邮箱需一致（若请求体提供）
    if request.email and request.email != email:
        raise ValidationError(message="邮箱不一致", field="email")

    # 去重并清理空白
    cleaned_tags = []
    seen = set()
    for t in (request.tags or []):
        tag = (t or "").strip()
        if not tag:
            continue
        if tag not in seen:
            seen.add(tag)
            cleaned_tags.append(tag)

    # 校验标签
    validate_tags(cleaned_tags)

    ok = await db_manager.set_account_tags(email, cleaned_tags)
    if ok:
        return ApiResponse(success=True, message="标签已保存", data={"email": email, "tags": cleaned_tags})
    raise DatabaseError(message="保存标签失败")

@router.post("/api/import")
async def import_accounts_dict(admin: AdminUser, request: ImportRequest) -> ApiResponse:
    """批量导入邮箱账户（需要管理员认证）

    使用 Pydantic 模型验证请求数据,确保数据格式正确

    请求体:
    {
        "accounts": [
            {
                "email": "user@example.com",
                "password": "optional",
                "client_id": "optional",
                "refresh_token": "required"
            }
        ],
        "merge_mode": "update"  // "update", "skip", "replace"
    }
    """
    try:

        logger.info(f"收到导入请求，账户数量: {len(request.accounts)}, 合并模式: {request.merge_mode}")

        # Pydantic 已经验证了数据格式,直接使用
        accounts = request.accounts
        merge_mode = request.merge_mode

        # 直接合并到数据库
        result = await merge_accounts_data_to_db(accounts, merge_mode)

        # 清除账户缓存以便重新加载
        if result.success and (result.added_count > 0 or result.updated_count > 0):
            await email_manager.invalidate_accounts_cache()

        return ApiResponse(
            success=result.success,
            message=result.message,
            data={
                "total_count": result.total_count,
                "added_count": result.added_count,
                "updated_count": result.updated_count,
                "skipped_count": result.skipped_count,
                "error_count": result.error_count,
                "details": result.details,
            }
        )

    except HTTPException as e:
        raise e
    except Exception as e:
        logger.exception(f"导入账户失败: {e}")
        return ApiResponse(
            success=False,
            message="导入失败，请检查数据格式或稍后重试",
            error_code="IMPORT_FAILED",
            data={
                "total_count": len(request.accounts),
                "added_count": 0,
                "updated_count": 0,
                "skipped_count": 0,
                "error_count": len(request.accounts),
                "details": [{"action": "error", "message": "系统错误，请联系管理员"}],
            }
        )

@router.post("/api/parse-import-text")
@handle_exceptions("解析导入文本")
async def parse_import_text(admin: AdminUser, request: ParseImportTextRequest) -> ApiResponse:
    """解析导入文本格式数据（需要管理员认证）

    使用 Pydantic 模型验证请求数据

    请求体:
    {
        "text": "email----password----refresh_token----client_id\\n..."
    }
    """
    import_text = request.text.strip()
    if not import_text:
        raise ValidationError(message="请提供要导入的文本数据", field="text")

    accounts = []
    errors = []

    lines = import_text.split('\n')
    for line_num, line in enumerate(lines, 1):
        try:
            parsed = parse_account_line(line)
            if not parsed:
                continue

            email, info = parsed
            accounts.append({
                "email": email,
                "password": info["password"],
                "client_id": info["client_id"],
                "refresh_token": info["refresh_token"]
            })
        except ValueError:
            errors.append(f"第{line_num}行格式错误")
        except Exception:
            errors.append(f"第{line_num}行解析失败")

    result_data = {
        "accounts": accounts,
        "parsed_count": len(accounts),
        "error_count": len(errors),
        "errors": errors
    }

    if errors:
        return ApiResponse(
            success=True,
            data=result_data,
            message=f"解析完成：成功 {len(accounts)} 条，错误 {len(errors)} 条"
        )
    else:
        return ApiResponse(
            success=True,
            data=result_data,
            message=f"解析成功：共 {len(accounts)} 条账户数据"
        )

@router.get("/api/export")
async def export_accounts_public(admin: AdminUser, format: str = "txt"):
    """导出账户配置（需要管理员认证）"""
    try:

        accounts = await load_accounts_config()

        if not accounts:
            raise ResourceNotFoundError("暂无账户数据", resource_type="accounts")

        export_lines = []
        export_lines.append("# Outlook邮件系统账号配置文件")
        export_lines.append(f"# 导出时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        export_lines.append("# 格式: 邮箱----密码----refresh_token----client_id")
        export_lines.append("# 注意：请妥善保管此文件，包含敏感信息")
        export_lines.append("")

        for email, account_info in accounts.items():
            password = account_info.get('password', '')
            refresh_token = account_info.get('refresh_token', '')
            client_id = account_info.get('client_id', settings.client_id)
            line = f"{email}----{password}----{refresh_token}----{client_id}"
            export_lines.append(line)

        export_content = "\n".join(export_lines)
        filename = f"outlook_accounts_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"

        return PlainTextResponse(
            content=export_content,
            headers={
                "Content-Disposition": f"attachment; filename={filename}",
                "Content-Type": "text/plain; charset=utf-8"
            }
        )

    except HTTPException as e:
        raise e
    except Exception as e:
        logger.exception(f"导出账户配置失败: {e}")
        raise ResourceNotFoundError("导出失败")
@router.post("/api/accounts", tags=["账户管理"])
async def create_account(
    admin: AdminUser,
    request: AccountCredentials,
) -> ApiResponse:
    """创建单个账户"""
    client_id = request.client_id or settings.client_id or ""
    success = await db_manager.add_account(
        request.email,
        password=request.password,
        client_id=client_id,
        refresh_token=request.refresh_token,
    )
    if not success:
        raise DuplicateEntryError(message="账户已存在或创建失败")

    await email_manager.invalidate_accounts_cache()
    return ApiResponse(success=True, data={"email": request.email}, message="账户已创建")


@router.put("/api/accounts/{email}", tags=["账户管理"])
async def update_account(
    email: str,
    admin: AdminUser,
    request: AccountCredentials,
) -> ApiResponse:
    """更新指定账户"""
    if request.email and request.email != email:
        raise ValidationError(message="邮箱与路径参数不一致", field="email")

    success = await db_manager.update_account(
        email,
        password=request.password,
        client_id=request.client_id or settings.client_id,
        refresh_token=request.refresh_token,
    )
    if not success:
        raise ResourceNotFoundError(message="账户不存在或更新失败", resource_type="account", resource_id=email)

    await email_manager.invalidate_accounts_cache()
    return ApiResponse(success=True, message="账户已更新", data={"email": email})


@router.delete("/api/accounts/{email}", tags=["账户管理"])
async def delete_account(
    email: str,
    admin: AdminUser,
    soft: bool = False,
) -> ApiResponse:
    """删除账户
    
    Args:
        email: 账户邮箱
        soft: 是否软删除（默认否，即物理删除）
    """
    if soft:
        # 软删除：标记删除但保留数据
        deleted = await db_manager.soft_delete_account(email)
        message = "账户已软删除（可恢复）"
    else:
        # 物理删除
        deleted = await db_manager.delete_account(email)
        message = "账户已永久删除"
    
    if not deleted:
        raise ResourceNotFoundError(message="账户不存在或删除失败", resource_type="account", resource_id=email)

    # 清理 IMAP 连接池中的连接
    await imap_pool.remove(email)
    await email_manager.invalidate_accounts_cache()
    return ApiResponse(success=True, message=message, data={"email": email, "soft_delete": soft})


@router.post("/api/accounts/batch-delete", tags=["批量操作"])
async def batch_delete_accounts(
    admin: AdminUser,
    request: dict[str, list[str] | bool],
) -> ApiResponse:
    """批量删除账户

    请求体:
    {
        "emails": ["email1@example.com", "email2@example.com"],
        "soft": false  // 可选，默认物理删除
    }
    """
    MAX_BATCH_SIZE = 100

    emails = request.get("emails", [])
    if not emails or not isinstance(emails, list):
        return ApiResponse(success=False, message="请提供要删除的账户列表")

    if len(emails) > MAX_BATCH_SIZE:
        return ApiResponse(success=False, message=f"批量操作最多支持 {MAX_BATCH_SIZE} 条记录，当前 {len(emails)} 条")

    soft_delete = bool(request.get("soft", False))

    if soft_delete:
        # 批量软删除
        deleted_count, failed_count = await db_manager.batch_soft_delete_accounts(emails)
        message = f"成功软删除 {deleted_count} 个账户（可恢复）"
    else:
        # 批量物理删除
        deleted_count, failed_count = await db_manager.batch_delete_accounts(emails)
        message = f"成功永久删除 {deleted_count} 个账户"
    
    if deleted_count > 0:
        # 批量清理 IMAP 连接池
        for email in emails:
            await imap_pool.remove(email)
        await email_manager.invalidate_accounts_cache()

    return ApiResponse(
        success=True,
        message=message,
        data={
            "deleted_count": deleted_count,
            "failed_count": failed_count,
            "requested_count": len(emails),
            "soft_delete": soft_delete,
        }
    )


@router.post("/api/accounts/batch-tags", tags=["批量操作"])
async def batch_update_tags(
    admin: AdminUser,
    request: dict[str, list[str] | str],
) -> ApiResponse:
    """批量更新账户标签

    请求体:
    {
        "emails": ["email1@example.com", "email2@example.com"],
        "tags": ["tag1", "tag2"],
        "mode": "add" | "remove" | "set"
    }
    """
    MAX_BATCH_SIZE = 100

    emails_raw = request.get("emails", [])
    tags_raw = request.get("tags", [])
    mode_raw = request.get("mode", "add")

    emails: list[str] = []
    if isinstance(emails_raw, list):
        emails = [str(e).strip() for e in emails_raw if str(e).strip()]
    elif isinstance(emails_raw, str):
        emails = [emails_raw.strip()] if emails_raw.strip() else []

    tags: list[str] = []
    if isinstance(tags_raw, list):
        tags = [str(t).strip() for t in tags_raw if str(t).strip()]
    elif isinstance(tags_raw, str):
        tags = [tags_raw.strip()] if tags_raw.strip() else []

    mode = mode_raw if isinstance(mode_raw, str) else str(mode_raw)

    if not emails:
        raise ValidationError(message="请提供要操作的账户列表", field="emails")
    if len(emails) > MAX_BATCH_SIZE:
        return ApiResponse(success=False, message=f"批量操作最多支持 {MAX_BATCH_SIZE} 条记录，当前 {len(emails)} 条")
    if mode not in ("add", "remove", "set"):
        raise ValidationError(message="无效的操作模式，支持: add, remove, set", field="mode")

    # 清理标签
    cleaned_tags = list({t.strip() for t in tags if t and t.strip()})

    # 校验标签（除非是 set 模式的空标签，用于清空）
    if cleaned_tags or mode != "set":
        validate_tags(cleaned_tags)

    updated_count, _ = await db_manager.batch_update_tags(emails, cleaned_tags, mode)

    return ApiResponse(
        success=True,
        message=f"成功更新 {updated_count} 个账户的标签",
        data={
            "updated_count": updated_count,
            "requested_count": len(emails),
            "tags": cleaned_tags,
            "mode": mode
        }
    )


@router.get("/api/accounts/{email}", tags=["账户管理"])
async def get_account_detail(
    email: str,
    admin: AdminUser,
) -> ApiResponse:
    """获取单个账户详情（敏感字段已脱敏）"""
    account = await db_manager.get_account(email)
    if not account:
        raise ResourceNotFoundError("账户不存在", resource_type="account", resource_id=email)

    return ApiResponse(
        success=True,
        data={
            "email": email,
            "client_id": account["client_id"],
            "has_password": bool(account["password"]),
            "has_refresh_token": bool(account["refresh_token"]),
            "password_preview": _mask_secret(account["password"]),
            "refresh_token_preview": _mask_secret(account["refresh_token"]),
            "is_used": bool(account.get("is_used")),
            "last_used_at": account.get("last_used_at"),
        },
    )


# ============================================================================
# 全局标签管理 API
# ============================================================================

@router.get("/api/tags", tags=["标签管理"])
@handle_exceptions("获取所有标签")
async def get_all_tags_list(admin: AdminUser) -> ApiResponse:
    """获取所有唯一标签列表（需要管理员认证）"""
    tags = await db_manager.get_all_tags()
    return ApiResponse(success=True, data={"tags": tags}, message=f"共 {len(tags)} 个标签")


@router.post("/api/tags", tags=["标签管理"])
@handle_exceptions("验证标签")
async def validate_tag(
    admin: AdminUser,
    request: dict[str, str],
) -> ApiResponse:
    """验证标签名称格式（需要管理员认证）

    验证标签名称是否符合格式要求，但不实际创建标签。
    标签会在被分配给账户时自动创建。

    请求体:
    {
        "name": "标签名称"
    }
    """
    tag_name = (request.get("name") or "").strip()
    if not tag_name:
        raise ValidationError(message="标签名称不能为空", field="name")

    # 校验标签格式
    validate_tags([tag_name])

    # 检查标签是否已存在
    existing_tags = await db_manager.get_all_tags()
    exists = tag_name in existing_tags

    return ApiResponse(
        success=True,
        message=f"标签 '{tag_name}' 格式有效" + ("（已存在）" if exists else "（可使用）"),
        data={"name": tag_name, "exists": exists}
    )


@router.delete("/api/tags/{tag_name}", tags=["标签管理"])
@handle_exceptions("删除标签")
async def delete_tag_globally(
    tag_name: str,
    admin: AdminUser,
) -> ApiResponse:
    """删除标签（从所有账户中移除，需要管理员认证）"""
    tag_name = tag_name.strip()
    if not tag_name:
        raise ValidationError(message="标签名称不能为空", field="tag_name")
    
    validate_tags([tag_name])

    # 检查标签是否存在
    existing_tags = await db_manager.get_all_tags()
    if tag_name not in existing_tags:
        raise ResourceNotFoundError(
            message=f"标签 '{tag_name}' 不存在",
            resource_type="tag",
            resource_id=tag_name
        )

    affected = await db_manager.delete_tag_globally(tag_name)

    return ApiResponse(
        success=True,
        message=f"已删除标签 '{tag_name}'，影响 {affected} 个账户",
        data={"tag": tag_name, "affected_accounts": affected}
    )


@router.put("/api/tags/{tag_name}", tags=["标签管理"])
@handle_exceptions("重命名标签")
async def rename_tag_globally(
    tag_name: str,
    admin: AdminUser,
    request: dict[str, str],
) -> ApiResponse:
    """重命名标签（在所有账户中，需要管理员认证）

    请求体:
    {
        "new_name": "新标签名称"
    }
    """
    tag_name = tag_name.strip()
    validate_tags([tag_name])
    new_name = (request.get("new_name") or "").strip()

    if not tag_name:
        raise ValidationError(message="原标签名称不能为空", field="tag_name")
    if not new_name:
        raise ValidationError(message="新标签名称不能为空", field="new_name")
    if tag_name == new_name:
        raise ValidationError(message="新名称与原名称相同", field="new_name")

    # 校验新标签格式
    validate_tags([new_name])

    # 检查原标签是否存在
    existing_tags = await db_manager.get_all_tags()
    if tag_name not in existing_tags:
        raise ResourceNotFoundError(
            message=f"标签 '{tag_name}' 不存在",
            resource_type="tag",
            resource_id=tag_name
        )

    # 检查新标签是否已存在
    if new_name in existing_tags:
        raise ValidationError(message=f"标签 '{new_name}' 已存在", field="new_name")

    affected = await db_manager.rename_tag_globally(tag_name, new_name)

    return ApiResponse(
        success=True,
        message=f"已将标签 '{tag_name}' 重命名为 '{new_name}'，影响 {affected} 个账户",
        data={"old_name": tag_name, "new_name": new_name, "affected_accounts": affected}
    )
