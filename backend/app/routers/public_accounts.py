import logging

from fastapi import APIRouter, Depends

from ..core.exceptions import DatabaseError, ResourceNotFoundError, ValidationError
from ..dependencies import enforce_public_rate_limit, verify_public_token
from ..models import ApiResponse
from ..services import (
    db_manager,
    email_manager,
    imap_pool,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/public", tags=["公共邮箱接口"])

@router.delete("/account/{email}", dependencies=[Depends(verify_public_token)])
async def delete_account_public(
    email: str,
    _: None = Depends(enforce_public_rate_limit),
) -> ApiResponse:
    """删除指定邮箱账户

    - 不需要管理员认证
    - 同时会删除关联的标签和邮件缓存
    """
    email = (email or "").strip()
    if not email:
        raise ValidationError(message="邮箱地址不能为空", field="email")

    try:
        deleted = await db_manager.delete_account(email)
        if not deleted:
            raise ResourceNotFoundError(message="账户不存在或删除失败", resource_type="account", resource_id=email)

        # 清理 IMAP 连接池中的连接
        await imap_pool.remove(email)
        # 删除账户后刷新邮件管理器缓存
        await email_manager.invalidate_accounts_cache()

        logger.info("通过公共接口删除账户: %s", email)
        return ApiResponse(
            success=True,
            message="账户已删除",
            data={"email": email},
        )
    except (ValidationError, ResourceNotFoundError):
        raise
    except Exception as exc:
        logger.error("通过公共接口删除账户失败(%s): %s", email, exc)
        raise DatabaseError(message="删除账户失败")

