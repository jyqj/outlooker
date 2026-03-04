import asyncio
import logging

from fastapi import APIRouter

from ..auth.oauth import get_access_token
from ..core.decorators import handle_exceptions
from ..dependencies import AdminUser, DbManager, EmailMgr
from ..models import ApiResponse
from ..services import load_accounts_config

logger = logging.getLogger(__name__)

router = APIRouter(tags=["仪表盘"])


@router.get("/api/dashboard/summary")
@handle_exceptions("获取仪表盘概要")
async def get_dashboard_summary(
    admin: AdminUser, db: DbManager
) -> ApiResponse:
    """聚合仪表盘所需的全部数据"""
    health_task = db.get_health_summary()
    tags_task = db.get_tag_statistics()
    events_task = db.get_audit_events(limit=5)

    health, tags, events = await asyncio.gather(health_task, tags_task, events_task)

    alerts: list[dict] = []
    expired = health.get("token_expired", 0)
    invalid = health.get("token_invalid", 0)
    errors = health.get("error", 0)
    if expired > 0:
        alerts.append(
            {
                "level": "warning",
                "message": f"{expired} 个账户 Token 已过期",
                "count": expired,
            }
        )
    if invalid > 0:
        alerts.append(
            {
                "level": "error",
                "message": f"{invalid} 个账户 Token 无效",
                "count": invalid,
            }
        )
    if errors > 0:
        alerts.append(
            {
                "level": "error",
                "message": f"{errors} 个账户检测异常",
                "count": errors,
            }
        )

    return ApiResponse(
        success=True,
        data={
            "health": health,
            "tags": tags,
            "alerts": alerts,
            "recent_events": events,
        },
    )


@router.post("/api/accounts/health-check")
@handle_exceptions("健康检测")
async def health_check_accounts(
    admin: AdminUser,
    db: DbManager,
    email_mgr: EmailMgr,
) -> ApiResponse:
    """批量检测所有账号的 token 有效性"""
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
                await db.update_account_health(email, "token_invalid")
                return
            try:
                access, new_rt = await get_access_token(rt, check_only=True)
                if access:
                    results[email] = "healthy"
                    await db.update_account_health(
                        email,
                        "healthy",
                        refresh_token=new_rt if new_rt and new_rt != rt else None,
                    )
                else:
                    results[email] = "token_expired"
                    await db.update_account_health(email, "token_expired")
            except Exception:
                results[email] = "error"
                await db.update_account_health(email, "error")

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
