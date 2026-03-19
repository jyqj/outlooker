import logging

from fastapi import APIRouter

from ..core.decorators import handle_exceptions
from ..core.exceptions import ResourceNotFoundError, ServiceUnavailableError
from ..dependencies import AdminUser, DbManager
from ..models import ApiResponse
from ..schemas.resources import (
    AuxEmailResourceBatchImportRequest,
    AuxEmailResourceCreateRequest,
    AuxEmailResourceRotateRequest,
    AuxEmailResourceUpdateRequest,
)
from ..services.channeling.resource_pool_service import (
    create_aux_email_resource,
    import_aux_email_resources,
    list_aux_email_resources,
    rotate_aux_email_resource,
    update_aux_email_resource,
)
from ..settings import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

router = APIRouter(tags=["Outlook资源池"])


def _ensure_resources_enabled() -> None:
    if not settings.outlook_features.resources_enabled:
        raise ServiceUnavailableError("资源池功能未启用")


@router.get("/api/outlook/resources/aux-emails")
@handle_exceptions("获取辅助邮箱资源列表")
async def get_aux_resources(
    admin: AdminUser,
    db: DbManager,
    status: str | None = None,
    channel_id: int | None = None,
    limit: int = 100,
    offset: int = 0,
) -> ApiResponse:
    _ensure_resources_enabled()
    data = await list_aux_email_resources(status=status, channel_id=channel_id, limit=limit, offset=offset)
    return ApiResponse(success=True, data=data)


@router.post("/api/outlook/resources/aux-emails")
@handle_exceptions("创建辅助邮箱资源")
async def create_aux_resource(
    admin: AdminUser,
    db: DbManager,
    request: AuxEmailResourceCreateRequest,
) -> ApiResponse:
    _ensure_resources_enabled()
    resource = await create_aux_email_resource(**request.model_dump())
    return ApiResponse(success=True, data=resource, message="辅助邮箱资源已创建")


@router.post("/api/outlook/resources/aux-emails/import")
@handle_exceptions("批量导入辅助邮箱资源")
async def import_aux_resources(
    admin: AdminUser,
    db: DbManager,
    request: AuxEmailResourceBatchImportRequest,
) -> ApiResponse:
    _ensure_resources_enabled()
    summary = await import_aux_email_resources([item.model_dump() for item in request.items])
    return ApiResponse(success=True, data=summary, message="辅助邮箱资源导入完成")


@router.put("/api/outlook/resources/aux-emails/{resource_id}")
@handle_exceptions("更新辅助邮箱资源")
async def put_aux_resource(
    resource_id: int,
    admin: AdminUser,
    db: DbManager,
    request: AuxEmailResourceUpdateRequest,
) -> ApiResponse:
    _ensure_resources_enabled()
    existing = await db._run_in_thread(
        lambda conn: conn.execute(
            "SELECT id FROM aux_email_resources WHERE id = ?",
            (resource_id,),
        ).fetchone()
    )
    if not existing:
        raise ResourceNotFoundError("辅助邮箱资源不存在", resource_type="aux_email_resource", resource_id=str(resource_id))
    payload = {key: value for key, value in request.model_dump().items() if value is not None}
    resource = await update_aux_email_resource(resource_id, **payload)
    return ApiResponse(success=True, data=resource, message="辅助邮箱资源已更新")


@router.post("/api/outlook/resources/aux-emails/{resource_id}/rotate")
@handle_exceptions("轮转辅助邮箱资源")
async def rotate_aux_resource(
    resource_id: int,
    admin: AdminUser,
    db: DbManager,
    request: AuxEmailResourceRotateRequest,
) -> ApiResponse:
    _ensure_resources_enabled()
    existing = await db.get_aux_email_resource_by_id(resource_id)
    if not existing:
        raise ResourceNotFoundError("辅助邮箱资源不存在", resource_type="aux_email_resource", resource_id=str(resource_id))
    result = await rotate_aux_email_resource(
        resource_id,
        replacement_address=request.replacement_address,
        max_fail_count=request.max_fail_count,
        reason=request.reason,
    )
    return ApiResponse(success=True, data=result, message="辅助邮箱资源轮转完成")
