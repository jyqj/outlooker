import logging

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from ..core.decorators import handle_exceptions
from ..core.exceptions import ResourceNotFoundError, ServiceUnavailableError, ValidationError
from ..dependencies import AdminUser, DbManager
from ..models import ApiResponse
from ..services.tasks.progress_event_service import iter_task_events, publish_task_event
from ..services.tasks.protocol_task_service import update_task_status
from ..settings import get_settings
from ..workers.protocol_tasks import protocol_bind_secondary, protocol_rebind_secondary

logger = logging.getLogger(__name__)
settings = get_settings()

router = APIRouter(tags=["Outlook任务中心"])


def _ensure_worker_enabled() -> None:
    if not settings.outlook_features.worker_enabled:
        raise ServiceUnavailableError("任务中心功能未启用")


@router.post("/api/outlook/tasks/{task_id}/cancel")
@handle_exceptions("取消 Outlook 任务")
async def cancel_outlook_task(
    task_id: int,
    admin: AdminUser,
    db: DbManager,
) -> ApiResponse:
    _ensure_worker_enabled()
    task = await db.get_protocol_task(task_id)
    if not task:
        raise ResourceNotFoundError("任务不存在", resource_type="protocol_task", resource_id=str(task_id))
    if task["status"] not in {"pending", "running", "waiting_code"}:
        raise ValidationError("当前状态不允许取消", field="status")
    await update_task_status(task_id, "cancelled")
    publish_task_event(task_id, "cancelled", {"by": admin})
    return ApiResponse(success=True, data={"task_id": task_id, "status": "cancelled"}, message="任务已取消")


@router.get("/api/outlook/tasks")
@handle_exceptions("获取 Outlook 任务列表")
async def list_outlook_tasks(
    admin: AdminUser,
    db: DbManager,
    status: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> ApiResponse:
    _ensure_worker_enabled()
    items = await db.list_protocol_tasks(status=status, limit=limit, offset=offset)
    return ApiResponse(success=True, data={"items": items, "total": len(items)})


@router.get("/api/outlook/tasks/{task_id}")
@handle_exceptions("获取 Outlook 任务详情")
async def get_outlook_task_detail(
    task_id: int,
    admin: AdminUser,
    db: DbManager,
) -> ApiResponse:
    _ensure_worker_enabled()
    task = await db.get_protocol_task(task_id)
    if not task:
        raise ResourceNotFoundError("任务不存在", resource_type="protocol_task", resource_id=str(task_id))
    steps = await db.list_protocol_task_steps(task_id)
    return ApiResponse(success=True, data={"task": task, "steps": steps})


@router.post("/api/outlook/tasks/{task_id}/retry")
@handle_exceptions("重试 Outlook 任务")
async def retry_outlook_task(
    task_id: int,
    admin: AdminUser,
    db: DbManager,
) -> ApiResponse:
    _ensure_worker_enabled()
    task = await db.get_protocol_task(task_id)
    if not task:
        raise ResourceNotFoundError("任务不存在", resource_type="protocol_task", resource_id=str(task_id))
    if task["status"] not in {"failed", "needs_manual"}:
        raise ValidationError("当前状态不允许重试", field="status")

    current_retry = int(task.get("retry_count") or 0)
    await update_task_status(task_id, "pending", error_message="", retry_count=current_retry + 1)
    publish_task_event(task_id, "retrying", {"by": admin, "retry_count": current_retry + 1})

    task_type = (task.get("task_type") or "").lower()
    if task_type in {"bind", "bind_secondary"}:
        protocol_bind_secondary.delay(task_id)
    elif task_type in {"rebind", "rebind_secondary"}:
        protocol_rebind_secondary.delay(task_id)
    else:
        raise ValidationError("未知任务类型，无法重试", field="task_type")

    return ApiResponse(
        success=True,
        data={"task_id": task_id, "status": "pending", "retry_count": current_retry + 1},
        message="任务已重新投递",
    )


@router.get("/api/outlook/tasks/events/stream")
async def stream_outlook_task_events(token: str) -> StreamingResponse:
    _ensure_worker_enabled()
    from ..auth.jwt import get_current_admin

    get_current_admin(f"Bearer {token}")
    return StreamingResponse(iter_task_events(), media_type="text/event-stream")
