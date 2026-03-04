import logging
from datetime import datetime

from fastapi import APIRouter
from fastapi.responses import PlainTextResponse

from ..core.decorators import handle_exceptions
from ..core.exceptions import DatabaseError, DuplicateEntryError, ResourceNotFoundError, ValidationError
from ..dependencies import AdminUser
from ..models import (
    AccountCredentials,
    AccountTagRequest,
    ApiResponse,
    BatchDeleteRequest,
    BatchTagsRequest,
    ImportRequest,
    ParseImportTextRequest,
    PickAccountRequest,
    RenameTagRequest,
    ValidateTagRequest,
    create_paginated_response,
)
from ..auth.oauth import get_access_token
from ..services import db_manager, email_manager, imap_pool, load_accounts_config, merge_accounts_data_to_db, parse_account_line
from ..settings import get_settings
from ..utils.pagination import paginate_items
from ..utils.validation import validate_tags

logger = logging.getLogger(__name__)

settings = get_settings()

router = APIRouter(tags=["账户管理"])
DEFAULT_ACCOUNT_PAGE_SIZE = 10
MAX_ACCOUNT_PAGE_SIZE = 100
MAX_BATCH_SIZE = 100


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
                "health_status": info.get("health_status", "unknown"),
                "last_health_check_at": info.get("last_health_check_at"),
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
    request: PickAccountRequest,
) -> ApiResponse:
    """随机取号：获取一个没有指定标签的账户并自动打标签"""
    tag = request.tag.strip()
    if not tag:
        raise ValidationError(message="请提供要打的标签", field="tag")

    validate_tags([tag])

    exclude_tags = [t.strip() for t in request.exclude_tags if t.strip()]
    if exclude_tags:
        validate_tags(exclude_tags)

    return_credentials = request.return_credentials

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

    logger.info("随机取号成功: %s, 标签: %s", email, tag)

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
@handle_exceptions("批量导入账户")
async def import_accounts_dict(admin: AdminUser, request: ImportRequest) -> ApiResponse:
    """批量导入邮箱账户（需要管理员认证）"""
    logger.info("收到导入请求，账户数量: %s, 合并模式: %s", len(request.accounts), request.merge_mode)

    accounts = request.accounts
    merge_mode = request.merge_mode

    result = await merge_accounts_data_to_db(accounts, merge_mode)

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
@handle_exceptions("导出账户配置")
async def export_accounts_public(admin: AdminUser, format: str = "txt"):
    """导出账户配置（需要管理员认证）"""
    accounts = await load_accounts_config()

    if not accounts:
        raise ResourceNotFoundError("暂无账户数据", resource_type="accounts")

    export_lines = [
        "# Outlook邮件系统账号配置文件",
        f"# 导出时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        "# 格式: 邮箱----密码----refresh_token----client_id",
        "# 注意：请妥善保管此文件，包含敏感信息",
        "",
    ]

    for email, account_info in accounts.items():
        password = account_info.get('password', '')
        refresh_token = account_info.get('refresh_token', '')
        client_id = account_info.get('client_id', settings.client_id)
        export_lines.append(f"{email}----{password}----{refresh_token}----{client_id}")

    export_content = "\n".join(export_lines)
    filename = f"outlook_accounts_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"

    return PlainTextResponse(
        content=export_content,
        headers={
            "Content-Disposition": f"attachment; filename={filename}",
            "Content-Type": "text/plain; charset=utf-8"
        }
    )
@router.post("/api/accounts", tags=["账户管理"])
@handle_exceptions("创建账户")
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
@handle_exceptions("更新账户")
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
@handle_exceptions("删除账户")
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
@handle_exceptions("批量删除账户")
async def batch_delete_accounts(
    admin: AdminUser,
    request: BatchDeleteRequest,
) -> ApiResponse:
    """批量删除账户"""
    emails = [e.strip() for e in request.emails if e.strip()]
    if not emails:
        raise ValidationError(message="请提供要删除的账户列表", field="emails")

    if len(emails) > MAX_BATCH_SIZE:
        raise ValidationError(
            message=f"批量操作最多支持 {MAX_BATCH_SIZE} 条记录，当前 {len(emails)} 条",
            field="emails",
        )

    soft_delete = request.soft

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
@handle_exceptions("批量更新标签")
async def batch_update_tags(
    admin: AdminUser,
    request: BatchTagsRequest,
) -> ApiResponse:
    """批量更新账户标签"""
    emails = [e.strip() for e in request.emails if e.strip()]
    tags: list[str] = [t.strip() for t in request.tags if t.strip()]
    mode = request.mode

    if not emails:
        raise ValidationError(message="请提供要操作的账户列表", field="emails")
    if len(emails) > MAX_BATCH_SIZE:
        raise ValidationError(
            message=f"批量操作最多支持 {MAX_BATCH_SIZE} 条记录，当前 {len(emails)} 条",
            field="emails",
        )
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
@handle_exceptions("获取账户详情")
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
    request: ValidateTagRequest,
) -> ApiResponse:
    """验证标签名称格式（需要管理员认证）

    验证标签名称是否符合格式要求，但不实际创建标签。
    标签会在被分配给账户时自动创建。
    """
    tag_name = request.name.strip()
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
    request: RenameTagRequest,
) -> ApiResponse:
    """重命名标签（在所有账户中，需要管理员认证）"""
    tag_name = tag_name.strip()
    validate_tags([tag_name])
    new_name = request.new_name.strip()

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


# ============================================================================
# 健康检测 API
# ============================================================================


@router.post("/api/accounts/health-check", tags=["健康检测"])
@handle_exceptions("健康检测")
async def health_check_accounts(
    admin: AdminUser,
) -> ApiResponse:
    """批量检测所有账号的 token 有效性"""
    import asyncio

    accounts = await load_accounts_config()
    if not accounts:
        return ApiResponse(success=True, message="没有账户", data={"total": 0})

    sem = asyncio.Semaphore(10)
    results: dict[str, str] = {}

    async def check_one(email: str, info: dict) -> None:
        async with sem:
            rt = info.get("refresh_token", "")
            if not rt:
                results[email] = "token_invalid"
                await db_manager.update_account_health(email, "token_invalid")
                return
            try:
                access, new_rt = await get_access_token(rt, check_only=True)
                if access:
                    results[email] = "healthy"
                    await db_manager.update_account_health(
                        email, "healthy",
                        refresh_token=new_rt if new_rt and new_rt != rt else None,
                    )
                else:
                    results[email] = "token_expired"
                    await db_manager.update_account_health(email, "token_expired")
            except Exception:
                results[email] = "error"
                await db_manager.update_account_health(email, "error")

    tasks = [check_one(e, info) for e, info in accounts.items()]
    await asyncio.gather(*tasks, return_exceptions=True)

    summary: dict[str, int] = {}
    for status in results.values():
        summary[status] = summary.get(status, 0) + 1

    return ApiResponse(
        success=True,
        message=f"检测完成 {len(results)} 个账户",
        data={"total": len(results), "summary": summary, "details": results},
    )


@router.get("/api/dashboard/summary", tags=["仪表盘"])
@handle_exceptions("获取仪表盘概要")
async def get_dashboard_summary(admin: AdminUser) -> ApiResponse:
    """聚合仪表盘所需的全部数据"""
    import asyncio

    health_task = db_manager.get_health_summary()
    tags_task = db_manager.get_tag_statistics()
    events_task = db_manager.get_audit_events(limit=5)

    health, tags, events = await asyncio.gather(health_task, tags_task, events_task)

    alerts: list[dict] = []
    expired = health.get("token_expired", 0)
    invalid = health.get("token_invalid", 0)
    errors = health.get("error", 0)
    if expired > 0:
        alerts.append({"level": "warning", "message": f"{expired} 个账户 Token 已过期", "count": expired})
    if invalid > 0:
        alerts.append({"level": "error", "message": f"{invalid} 个账户 Token 无效", "count": invalid})
    if errors > 0:
        alerts.append({"level": "error", "message": f"{errors} 个账户检测异常", "count": errors})

    return ApiResponse(
        success=True,
        data={
            "health": health,
            "tags": tags,
            "alerts": alerts,
            "recent_events": events,
        },
    )
