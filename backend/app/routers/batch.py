import logging

from fastapi import APIRouter

from ..core.decorators import handle_exceptions
from ..core.exceptions import ValidationError
from ..dependencies import AdminUser, DbManager, EmailMgr, ImapPool
from ..models import ApiResponse, BatchDeleteRequest, BatchTagsRequest
from ..utils.validation import validate_tags

logger = logging.getLogger(__name__)

router = APIRouter(tags=["批量操作"])

MAX_BATCH_SIZE = 100


@router.post("/api/accounts/batch-delete")
@handle_exceptions("批量删除账户")
async def batch_delete_accounts(
    admin: AdminUser,
    db: DbManager,
    email_mgr: EmailMgr,
    pool: ImapPool,
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
        deleted_count, failed_count = await db.batch_soft_delete_accounts(emails)
        message = f"成功软删除 {deleted_count} 个账户（可恢复）"
    else:
        deleted_count, failed_count = await db.batch_delete_accounts(emails)
        message = f"成功永久删除 {deleted_count} 个账户"

    if deleted_count > 0:
        for email in emails:
            await pool.remove(email)
        await email_mgr.invalidate_accounts_cache()

    return ApiResponse(
        success=True,
        message=message,
        data={
            "deleted_count": deleted_count,
            "failed_count": failed_count,
            "requested_count": len(emails),
            "soft_delete": soft_delete,
        },
    )


@router.post("/api/accounts/batch-tags")
@handle_exceptions("批量更新标签")
async def batch_update_tags(
    admin: AdminUser,
    db: DbManager,
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
        raise ValidationError(
            message="无效的操作模式，支持: add, remove, set", field="mode"
        )

    cleaned_tags = list({t.strip() for t in tags if t and t.strip()})

    if cleaned_tags or mode != "set":
        validate_tags(cleaned_tags)

    updated_count, _ = await db.batch_update_tags(emails, cleaned_tags, mode)

    return ApiResponse(
        success=True,
        message=f"成功更新 {updated_count} 个账户的标签",
        data={
            "updated_count": updated_count,
            "requested_count": len(emails),
            "tags": cleaned_tags,
            "mode": mode,
        },
    )
