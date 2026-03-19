import logging

from fastapi import APIRouter, Depends

from ..core.exceptions import DatabaseError, ResourceNotFoundError, ValidationError
from ..dependencies import DbManager, EmailMgr, ImapPool, enforce_public_rate_limit, verify_public_token
from ..models import ApiResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/public", tags=["公共邮箱接口"])


@router.get("/account-unused", dependencies=[Depends(verify_public_token)])
async def get_unused_account_public(
    db: DbManager,
    _: None = Depends(enforce_public_rate_limit),
) -> ApiResponse:
    """获取一个未使用的账户。"""
    account = await db.get_unused_account()
    if not account:
        return ApiResponse(success=False, message="暂无未使用的邮箱", data=None)

    return ApiResponse(
        success=True,
        message="获取未使用邮箱成功",
        data={
            "email": account["email"],
            "password": account.get("password", ""),
            "client_id": account.get("client_id", ""),
            "refresh_token": account.get("refresh_token", ""),
        },
    )


@router.post("/account/{email}/used", dependencies=[Depends(verify_public_token)])
async def mark_account_used_public(
    email: str,
    db: DbManager,
    _: None = Depends(enforce_public_rate_limit),
) -> ApiResponse:
    """标记指定邮箱已被消耗。"""
    email = (email or "").strip()
    if not email:
        raise ValidationError(message="邮箱地址不能为空", field="email")

    marked = await db.mark_account_used(email)
    if not marked:
        raise ResourceNotFoundError(
            message="账户不存在或标记失败",
            resource_type="account",
            resource_id=email,
        )

    logger.info("通过公共接口标记账户已使用: %s", email)
    return ApiResponse(
        success=True,
        message="账户已标记为已使用",
        data={"email": email},
    )


@router.delete("/account/{email}", dependencies=[Depends(verify_public_token)])
async def delete_account_public(
    email: str,
    db: DbManager,
    email_mgr: EmailMgr,
    pool: ImapPool,
    _: None = Depends(enforce_public_rate_limit),
) -> ApiResponse:
    """删除指定邮箱账户（不需要管理员认证）"""
    email = (email or "").strip()
    if not email:
        raise ValidationError(message="邮箱地址不能为空", field="email")

    try:
        deleted = await db.delete_account(email)
        if not deleted:
            raise ResourceNotFoundError(
                message="账户不存在或删除失败",
                resource_type="account",
                resource_id=email,
            )

        await pool.remove(email)
        await email_mgr.invalidate_accounts_cache()

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
        raise DatabaseError(message="删除账户失败") from exc
