import logging

from fastapi import APIRouter

from ..core.decorators import handle_exceptions
from ..core.exceptions import ServiceUnavailableError
from ..dependencies import AdminUser
from ..models import ApiResponse
from ..schemas.outlook_protocol import (
    ProtocolBindRequest,
    ProtocolListProofsRequest,
    ProtocolLoginRequest,
    ProtocolReplaceRequest,
)
from ..services.outlook.protocol import OutlookProtocolError, OutlookProtocolClient, build_protocol_client_for_channel
from ..services.outlook.protocol_code_provider import StaticCodeProvider
from ..settings import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

router = APIRouter(tags=["Outlook协议管理"])


def _ensure_protocol_enabled() -> None:
    if not settings.outlook_features.protocol_enabled:
        raise ServiceUnavailableError("协议功能未启用")


@router.post("/api/outlook/protocol/test-login")
@handle_exceptions("测试 Outlook 协议登录")
async def test_protocol_login(admin: AdminUser, request: ProtocolLoginRequest) -> ApiResponse:
    _ensure_protocol_enabled()
    async with await build_protocol_client_for_channel(request.channel_id) as client:
        data = await client.login(request.email, request.password)
    return ApiResponse(success=True, data=data, message="协议登录成功")


@router.post("/api/outlook/protocol/list-proofs")
@handle_exceptions("列出 Outlook 协议验证方式")
async def list_protocol_proofs(admin: AdminUser, request: ProtocolListProofsRequest) -> ApiResponse:
    _ensure_protocol_enabled()
    async with await build_protocol_client_for_channel(request.channel_id) as client:
        await client.login(request.email, request.password)
        data = await client.list_proofs()
    return ApiResponse(success=True, data=data)


@router.post("/api/outlook/protocol/bind")
@handle_exceptions("绑定 Outlook 恢复邮箱")
async def bind_protocol_recovery_email(admin: AdminUser, request: ProtocolBindRequest) -> ApiResponse:
    _ensure_protocol_enabled()
    provider = StaticCodeProvider(request.static_code)
    async with await build_protocol_client_for_channel(request.channel_id) as client:
        await client.login(request.email, request.password)
        if request.verification_email:
            await client.verify_identity(request.verification_email, provider)
        data = await client.add_recovery_email(request.recovery_email, provider)
    return ApiResponse(success=True, data=data, message="恢复邮箱绑定完成")


@router.post("/api/outlook/protocol/replace")
@handle_exceptions("替换 Outlook 恢复邮箱")
async def replace_protocol_recovery_email(admin: AdminUser, request: ProtocolReplaceRequest) -> ApiResponse:
    _ensure_protocol_enabled()
    provider = StaticCodeProvider(request.static_code)
    async with await build_protocol_client_for_channel(request.channel_id) as client:
        await client.login(request.email, request.password)
        data = await client.replace_recovery_email(
            old_email=request.old_email,
            new_email=request.new_email,
            code_provider=provider,
            verification_email=request.verification_email,
        )
    return ApiResponse(success=True, data=data, message="恢复邮箱替换完成")
