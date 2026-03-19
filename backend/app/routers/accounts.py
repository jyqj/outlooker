import logging
from datetime import datetime

from fastapi import APIRouter
from fastapi.responses import PlainTextResponse

from ..core.decorators import handle_exceptions
from ..core.exceptions import (
    DatabaseError,
    DuplicateEntryError,
    ResourceNotFoundError,
    ValidationError,
)
from ..dependencies import AdminUser, DbManager, EmailMgr, ImapPool
from ..models import (
    AccountCredentials,
    ApiResponse,
    ImportRequest,
    ParseImportTextRequest,
    PickAccountRequest,
    create_paginated_response,
)
from ..services import load_accounts_config, merge_accounts_data_to_db, parse_account_line
from ..services.channeling.allocation_service import allocate_account_for_channel
from ..settings import get_settings
from ..utils.pagination import paginate_items
from ..utils.validation import validate_tags

logger = logging.getLogger(__name__)

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
            "is_used": bool(info.get("is_used")),
            "last_used_at": info.get("last_used_at"),
        }
        for email, info in accounts.items()
    ]
    return ApiResponse(
        success=True, data=account_list, message=f"共 {len(account_list)} 个账户"
    )


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

    items_page, total = paginate_items(
        emails,
        max(1, page),
        max(1, min(MAX_ACCOUNT_PAGE_SIZE, page_size)),
    )

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
        message=f"共 {total} 个账户",
    )


@router.post("/api/accounts/pick")
@handle_exceptions("随机取号")
async def pick_random_account(
    admin: AdminUser,
    db: DbManager,
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

    account = None
    if settings.outlook_features.channels_enabled and not exclude_tags:
        channel = await db.get_channel_by_code_or_name(tag)
        if channel and channel.get("status") == "active":
            try:
                allocation = await allocate_account_for_channel(
                    int(channel["id"]),
                    leased_to=f"legacy-pick:{admin}",
                )
                account_email = allocation["account_email"]
                outlook_account = await db.get_outlook_account(account_email)
                source_email = (
                    outlook_account.get("source_account_email")
                    if outlook_account and outlook_account.get("source_account_email")
                    else account_email
                )
                source_info = await db.get_account(source_email)
                if source_info:
                    account = {
                        "email": source_email,
                        "password": source_info.get("password", ""),
                        "client_id": source_info.get("client_id", ""),
                        "refresh_token": source_info.get("refresh_token", ""),
                        "tags": await db.get_account_tags(source_email),
                    }
            except Exception:
                account = None

    if account is None:
        account = await db.get_random_account_without_tag(tag, exclude_tags)

    if not account:
        raise ResourceNotFoundError(
            message=f"没有找到可用的账户（不含标签 '{tag}'）",
            resource_type="account",
        )

    email = account["email"]
    current_tags = account.get("tags", [])

    new_tags = list(set(current_tags + [tag]))
    ok = await db.set_account_tags(email, new_tags)
    if not ok:
        raise DatabaseError(message="标记账户失败")

    response_data: dict = {
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
        data=response_data,
    )


@router.post("/api/import")
@handle_exceptions("批量导入账户")
async def import_accounts_dict(
    admin: AdminUser,
    email_mgr: EmailMgr,
    request: ImportRequest,
) -> ApiResponse:
    """批量导入邮箱账户（需要管理员认证）"""
    logger.info(
        "收到导入请求，账户数量: %s, 合并模式: %s",
        len(request.accounts),
        request.merge_mode,
    )

    result = await merge_accounts_data_to_db(request.accounts, request.merge_mode)

    if result.success and (result.added_count > 0 or result.updated_count > 0):
        await email_mgr.invalidate_accounts_cache()

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
        },
    )


@router.post("/api/parse-import-text")
@handle_exceptions("解析导入文本")
async def parse_import_text(
    admin: AdminUser, request: ParseImportTextRequest
) -> ApiResponse:
    """解析导入文本格式数据（需要管理员认证）"""
    import_text = request.text.strip()
    if not import_text:
        raise ValidationError(message="请提供要导入的文本数据", field="text")

    accounts = []
    errors = []

    lines = import_text.split("\n")
    for line_num, line in enumerate(lines, 1):
        try:
            parsed = parse_account_line(line)
            if not parsed:
                continue

            email, info = parsed
            accounts.append(
                {
                    "email": email,
                    "password": info["password"],
                    "client_id": info["client_id"],
                    "refresh_token": info["refresh_token"],
                    "recovery_email": info.get("recovery_email", ""),
                    "recovery_password": info.get("recovery_password", ""),
                }
            )
        except ValueError:
            errors.append(f"第{line_num}行格式错误")
        except Exception:
            errors.append(f"第{line_num}行解析失败")

    result_data = {
        "accounts": accounts,
        "parsed_count": len(accounts),
        "error_count": len(errors),
        "errors": errors,
    }

    if errors:
        return ApiResponse(
            success=True,
            data=result_data,
            message=f"解析完成：成功 {len(accounts)} 条，错误 {len(errors)} 条",
        )
    else:
        return ApiResponse(
            success=True,
            data=result_data,
            message=f"解析成功：共 {len(accounts)} 条账户数据",
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
        password = account_info.get("password", "")
        refresh_token = account_info.get("refresh_token", "")
        client_id = account_info.get("client_id", settings.client_id)
        export_lines.append(f"{email}----{password}----{refresh_token}----{client_id}")

    export_content = "\n".join(export_lines)
    filename = f"outlook_accounts_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"

    return PlainTextResponse(
        content=export_content,
        headers={
            "Content-Disposition": f"attachment; filename={filename}",
            "Content-Type": "text/plain; charset=utf-8",
        },
    )


@router.post("/api/accounts")
@handle_exceptions("创建账户")
async def create_account(
    admin: AdminUser,
    db: DbManager,
    email_mgr: EmailMgr,
    request: AccountCredentials,
) -> ApiResponse:
    """创建单个账户"""
    client_id = request.client_id or settings.client_id or ""
    success = await db.add_account(
        request.email,
        password=request.password,
        client_id=client_id,
        refresh_token=request.refresh_token,
    )
    if not success:
        raise DuplicateEntryError(message="账户已存在或创建失败")

    await email_mgr.invalidate_accounts_cache()
    return ApiResponse(
        success=True, data={"email": request.email}, message="账户已创建"
    )


@router.put("/api/accounts/{email}")
@handle_exceptions("更新账户")
async def update_account(
    email: str,
    admin: AdminUser,
    db: DbManager,
    email_mgr: EmailMgr,
    request: AccountCredentials,
) -> ApiResponse:
    """更新指定账户"""
    if request.email and request.email != email:
        raise ValidationError(message="邮箱与路径参数不一致", field="email")

    success = await db.update_account(
        email,
        password=request.password,
        client_id=request.client_id or settings.client_id,
        refresh_token=request.refresh_token,
    )
    if not success:
        raise ResourceNotFoundError(
            message="账户不存在或更新失败",
            resource_type="account",
            resource_id=email,
        )

    await email_mgr.invalidate_accounts_cache()
    return ApiResponse(success=True, message="账户已更新", data={"email": email})


@router.delete("/api/accounts/{email}")
@handle_exceptions("删除账户")
async def delete_account(
    email: str,
    admin: AdminUser,
    db: DbManager,
    email_mgr: EmailMgr,
    pool: ImapPool,
    soft: bool = False,
) -> ApiResponse:
    """删除账户"""
    if soft:
        deleted = await db.soft_delete_account(email)
        message = "账户已软删除（可恢复）"
    else:
        deleted = await db.delete_account(email)
        message = "账户已永久删除"

    if not deleted:
        raise ResourceNotFoundError(
            message="账户不存在或删除失败",
            resource_type="account",
            resource_id=email,
        )

    await pool.remove(email)
    await email_mgr.invalidate_accounts_cache()
    return ApiResponse(
        success=True,
        message=message,
        data={"email": email, "soft_delete": soft},
    )


@router.get("/api/accounts/{email}")
@handle_exceptions("获取账户详情")
async def get_account_detail(
    email: str,
    admin: AdminUser,
    db: DbManager,
) -> ApiResponse:
    """获取单个账户详情（敏感字段已脱敏）"""
    account = await db.get_account(email)
    if not account:
        raise ResourceNotFoundError(
            "账户不存在", resource_type="account", resource_id=email
        )

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
