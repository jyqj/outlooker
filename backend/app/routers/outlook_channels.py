import logging

from fastapi import APIRouter

from ..core.decorators import handle_exceptions
from ..core.exceptions import ResourceNotFoundError, ServiceUnavailableError
from ..dependencies import AdminUser, DbManager
from ..models import ApiResponse
from ..schemas.channels import (
    ChannelBindAccountsRequest,
    ChannelBindResourcesRequest,
    ChannelCreateRequest,
    ChannelUpdateRequest,
)
from ..services.channeling.allocation_service import (
    bind_accounts_to_channel,
    create_channel as create_channel_service,
    list_channels as list_channels_service,
    update_channel as update_channel_service,
)
from ..services.channeling.channel_stats_service import get_channel_stats
from ..services.channeling.resource_pool_service import bind_resources_to_channel
from ..settings import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

router = APIRouter(tags=["Outlook渠道管理"])


def _ensure_channels_enabled() -> None:
    if not settings.outlook_features.channels_enabled:
        raise ServiceUnavailableError("渠道功能未启用")


@router.get("/api/outlook/channels")
@handle_exceptions("获取 Outlook 渠道列表")
async def list_outlook_channels(admin: AdminUser, db: DbManager) -> ApiResponse:
    _ensure_channels_enabled()
    channels = await list_channels_service()
    return ApiResponse(success=True, data={"items": channels, "total": len(channels)})


@router.post("/api/outlook/channels")
@handle_exceptions("创建 Outlook 渠道")
async def create_outlook_channel(
    admin: AdminUser,
    db: DbManager,
    request: ChannelCreateRequest,
) -> ApiResponse:
    _ensure_channels_enabled()
    channel = await create_channel_service(**request.model_dump())
    return ApiResponse(success=True, data=channel, message="渠道已创建")


@router.put("/api/outlook/channels/{channel_id}")
@handle_exceptions("更新 Outlook 渠道")
async def update_outlook_channel(
    channel_id: int,
    admin: AdminUser,
    db: DbManager,
    request: ChannelUpdateRequest,
) -> ApiResponse:
    _ensure_channels_enabled()
    existing = await db.get_channel(channel_id)
    if not existing:
        raise ResourceNotFoundError("渠道不存在", resource_type="channel", resource_id=str(channel_id))
    payload = {key: value for key, value in request.model_dump().items() if value is not None}
    channel = await update_channel_service(channel_id, **payload)
    return ApiResponse(success=True, data=channel, message="渠道已更新")


@router.post("/api/outlook/channels/{channel_id}/accounts/bind")
@handle_exceptions("绑定渠道账户")
async def bind_channel_accounts(
    channel_id: int,
    admin: AdminUser,
    db: DbManager,
    request: ChannelBindAccountsRequest,
) -> ApiResponse:
    _ensure_channels_enabled()
    existing = await db.get_channel(channel_id)
    if not existing:
        raise ResourceNotFoundError("渠道不存在", resource_type="channel", resource_id=str(channel_id))
    summary = await bind_accounts_to_channel(
        channel_id,
        request.emails,
        status=request.status,
        weight=request.weight,
    )
    return ApiResponse(success=True, data=summary, message="渠道账户绑定完成")


@router.post("/api/outlook/channels/{channel_id}/resources/bind")
@handle_exceptions("绑定渠道资源")
async def bind_channel_resources(
    channel_id: int,
    admin: AdminUser,
    db: DbManager,
    request: ChannelBindResourcesRequest,
) -> ApiResponse:
    _ensure_channels_enabled()
    existing = await db.get_channel(channel_id)
    if not existing:
        raise ResourceNotFoundError("渠道不存在", resource_type="channel", resource_id=str(channel_id))
    summary = await bind_resources_to_channel(
        channel_id,
        request.resource_ids,
        status=request.status,
    )
    return ApiResponse(success=True, data=summary, message="渠道资源绑定完成")


@router.get("/api/outlook/channels/stats")
@handle_exceptions("获取渠道统计")
async def get_outlook_channel_stats(
    admin: AdminUser,
    db: DbManager,
    channel_id: int | None = None,
) -> ApiResponse:
    _ensure_channels_enabled()
    stats = await get_channel_stats(channel_id)
    return ApiResponse(success=True, data=stats)
