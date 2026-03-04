import logging

from fastapi import APIRouter

from ..core.decorators import handle_exceptions
from ..core.exceptions import (
    DatabaseError,
    ResourceNotFoundError,
    ValidationError,
)
from ..dependencies import AdminUser, DbManager
from ..models import (
    AccountTagRequest,
    ApiResponse,
    RenameTagRequest,
    ValidateTagRequest,
)
from ..utils.validation import validate_tags

logger = logging.getLogger(__name__)

router = APIRouter(tags=["标签管理"])


@router.get("/api/accounts/tags")
@handle_exceptions("获取账户标签")
async def get_accounts_tags(admin: AdminUser, db: DbManager) -> ApiResponse:
    """获取所有标签和账户-标签映射（需要管理员认证）"""
    tags = await db.get_all_tags()
    accounts_map = await db.get_accounts_with_tags()
    return ApiResponse(success=True, data={"tags": tags, "accounts": accounts_map})


@router.get("/api/accounts/tags/stats")
@handle_exceptions("获取标签统计")
async def get_tag_statistics(admin: AdminUser, db: DbManager) -> ApiResponse:
    """获取标签使用统计（需要管理员认证）"""
    stats = await db.get_tag_statistics()
    return ApiResponse(success=True, data=stats)


@router.get("/api/accounts/{email}/tags")
@handle_exceptions("获取账户标签")
async def get_account_tags(
    email: str, admin: AdminUser, db: DbManager
) -> ApiResponse:
    """获取指定账户的标签（需要管理员认证）"""
    tags = await db.get_account_tags(email)
    return ApiResponse(success=True, data={"email": email, "tags": tags})


@router.post("/api/accounts/{email}/tags")
@handle_exceptions("保存账户标签")
async def set_account_tags(
    email: str,
    admin: AdminUser,
    db: DbManager,
    request: AccountTagRequest,
) -> ApiResponse:
    """设置指定账户的标签（需要管理员认证）"""
    if request.email and request.email != email:
        raise ValidationError(message="邮箱不一致", field="email")

    cleaned_tags: list[str] = []
    seen: set[str] = set()
    for t in request.tags or []:
        tag = (t or "").strip()
        if not tag:
            continue
        if tag not in seen:
            seen.add(tag)
            cleaned_tags.append(tag)

    validate_tags(cleaned_tags)

    ok = await db.set_account_tags(email, cleaned_tags)
    if ok:
        return ApiResponse(
            success=True,
            message="标签已保存",
            data={"email": email, "tags": cleaned_tags},
        )
    raise DatabaseError(message="保存标签失败")


@router.get("/api/tags")
@handle_exceptions("获取所有标签")
async def get_all_tags_list(admin: AdminUser, db: DbManager) -> ApiResponse:
    """获取所有唯一标签列表（需要管理员认证）"""
    tags = await db.get_all_tags()
    return ApiResponse(
        success=True, data={"tags": tags}, message=f"共 {len(tags)} 个标签"
    )


@router.post("/api/tags")
@handle_exceptions("验证标签")
async def validate_tag(
    admin: AdminUser,
    db: DbManager,
    request: ValidateTagRequest,
) -> ApiResponse:
    """验证标签名称格式（需要管理员认证）"""
    tag_name = request.name.strip()
    if not tag_name:
        raise ValidationError(message="标签名称不能为空", field="name")

    validate_tags([tag_name])

    existing_tags = await db.get_all_tags()
    exists = tag_name in existing_tags

    return ApiResponse(
        success=True,
        message=f"标签 '{tag_name}' 格式有效" + ("（已存在）" if exists else "（可使用）"),
        data={"name": tag_name, "exists": exists},
    )


@router.delete("/api/tags/{tag_name}")
@handle_exceptions("删除标签")
async def delete_tag_globally(
    tag_name: str,
    admin: AdminUser,
    db: DbManager,
) -> ApiResponse:
    """删除标签（从所有账户中移除，需要管理员认证）"""
    tag_name = tag_name.strip()
    if not tag_name:
        raise ValidationError(message="标签名称不能为空", field="tag_name")

    validate_tags([tag_name])

    existing_tags = await db.get_all_tags()
    if tag_name not in existing_tags:
        raise ResourceNotFoundError(
            message=f"标签 '{tag_name}' 不存在",
            resource_type="tag",
            resource_id=tag_name,
        )

    affected = await db.delete_tag_globally(tag_name)

    return ApiResponse(
        success=True,
        message=f"已删除标签 '{tag_name}'，影响 {affected} 个账户",
        data={"tag": tag_name, "affected_accounts": affected},
    )


@router.put("/api/tags/{tag_name}")
@handle_exceptions("重命名标签")
async def rename_tag_globally(
    tag_name: str,
    admin: AdminUser,
    db: DbManager,
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

    validate_tags([new_name])

    existing_tags = await db.get_all_tags()
    if tag_name not in existing_tags:
        raise ResourceNotFoundError(
            message=f"标签 '{tag_name}' 不存在",
            resource_type="tag",
            resource_id=tag_name,
        )

    if new_name in existing_tags:
        raise ValidationError(message=f"标签 '{new_name}' 已存在", field="new_name")

    affected = await db.rename_tag_globally(tag_name, new_name)

    return ApiResponse(
        success=True,
        message=f"已将标签 '{tag_name}' 重命名为 '{new_name}'，影响 {affected} 个账户",
        data={
            "old_name": tag_name,
            "new_name": new_name,
            "affected_accounts": affected,
        },
    )
