import json
import logging

from fastapi import APIRouter

from ..core.decorators import handle_exceptions
from ..core.exceptions import ResourceNotFoundError, ServiceUnavailableError, ValidationError
from ..dependencies import AdminUser, DbManager
from ..models import ApiResponse
from ..schemas.outlook_protocol import (
    ProtocolBindRequest,
    ProtocolListProofsRequest,
    ProtocolLoginRequest,
    ProtocolReplaceRequest,
)
from ..services.outlook.protocol import OutlookProtocolError, OutlookProtocolClient, build_protocol_client_for_channel
from ..services.outlook.protocol_code_provider import StaticCodeProvider
from ..services.channeling.resource_pool_service import create_aux_email_resource, get_allocatable_resource_for_channel
from ..services.tasks.progress_event_service import publish_task_event
from ..services.tasks.protocol_task_service import add_task_step
from ..workers.protocol_tasks import protocol_bind_secondary, protocol_rebind_secondary
from ..settings import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

router = APIRouter(tags=["Outlook协议管理"])


def _ensure_protocol_enabled() -> None:
    if not settings.outlook_features.protocol_enabled:
        raise ServiceUnavailableError("协议功能未启用")


def _parse_notes(raw: str | None) -> dict[str, object]:
    if not raw:
        return {}
    try:
        return json.loads(raw)
    except Exception:
        return {}


async def _ensure_login_account(db: DbManager, email: str, password: str) -> None:
    existing = await db.get_account(email)
    if existing is None:
        await db.add_account(email, password=password)
        return
    if password and existing.get("password") != password:
        await db.update_account(email, password=password)


async def _prepare_resource(
    db: DbManager,
    *,
    target_email: str,
    address: str,
    channel_id: int | None,
    static_code: str,
) -> dict[str, object]:
    normalized_address = (address or "").strip().lower()

    if normalized_address:
        resource = await db.get_aux_email_resource_by_address(normalized_address)
        if resource is None:
            resource = await create_aux_email_resource(
                address=normalized_address,
                provider="custom",
                source_type="manual",
                status="available",
                channel_id=channel_id,
                notes=json.dumps(
                    {
                        "source": "protocol_queue",
                        "static_code": static_code,
                    },
                    ensure_ascii=False,
                ),
            )
        else:
            bound_account_email = (resource.get("bound_account_email") or "").strip().lower()
            if resource.get("status") == "bound" and bound_account_email not in {
                "",
                target_email.lower(),
            }:
                raise ValidationError("辅助邮箱已绑定其他账户", field="recovery_email")

            notes = _parse_notes(resource.get("notes"))
            updates: dict[str, object] = {}
            if static_code and notes.get("static_code") != static_code:
                notes["static_code"] = static_code
                updates["notes"] = json.dumps(notes, ensure_ascii=False)
            if channel_id is not None and resource.get("channel_id") != channel_id:
                updates["channel_id"] = channel_id
            if updates:
                await db.update_aux_email_resource(int(resource["id"]), **updates)
                resource = await db.get_aux_email_resource_by_id(int(resource["id"])) or resource
    else:
        if channel_id is None:
            raise ValidationError("未提供辅助邮箱且未指定渠道", field="channel_id")
        resource = await get_allocatable_resource_for_channel(channel_id)
        if resource is None:
            raise ResourceNotFoundError(
                "渠道下没有可用的辅助邮箱资源",
                resource_type="aux_email_resource",
                resource_id=str(channel_id),
            )
        notes = _parse_notes(resource.get("notes"))
        if static_code and notes.get("static_code") != static_code:
            notes["static_code"] = static_code
            await db.update_aux_email_resource(
                int(resource["id"]),
                notes=json.dumps(notes, ensure_ascii=False),
            )
            resource = await db.get_aux_email_resource_by_id(int(resource["id"])) or resource

    if channel_id is not None:
        await db.bind_resource_to_channel(channel_id, int(resource["id"]), status="active")

    notes = _parse_notes(resource.get("notes"))
    if not notes.get("static_code"):
        raise ValidationError(
            "当前异步协议任务需要 static_code 或资源中预置 static_code",
            field="static_code",
        )
    return resource


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
async def bind_protocol_recovery_email(
    admin: AdminUser,
    db: DbManager,
    request: ProtocolBindRequest,
) -> ApiResponse:
    _ensure_protocol_enabled()
    if request.queue:
        await _ensure_login_account(db, request.email, request.password)
        resource = await _prepare_resource(
            db,
            target_email=request.email,
            address=request.recovery_email,
            channel_id=request.channel_id,
            static_code=request.static_code,
        )
        task_id = await db.create_protocol_task(
            task_type="bind_secondary",
            target_email=request.email,
            verification_email=(request.verification_email or "").strip(),
            channel_id=request.channel_id,
            resource_id=int(resource["id"]),
            status="pending",
        )
        await add_task_step(
            task_id,
            "queued",
            status="success",
            detail=json.dumps(
                {
                    "task_type": "bind_secondary",
                    "resource": resource["address"],
                    "queued_by": admin,
                },
                ensure_ascii=False,
            ),
        )
        publish_task_event(
            task_id,
            "queued",
            {"task_type": "bind_secondary", "resource": resource["address"], "queued_by": admin},
        )
        protocol_bind_secondary.delay(task_id)
        return ApiResponse(
            success=True,
            data={
                "task_id": task_id,
                "status": "pending",
                "resource_id": int(resource["id"]),
                "resource_address": resource["address"],
            },
            message="恢复邮箱绑定任务已创建",
        )

    provider = StaticCodeProvider(request.static_code)
    async with await build_protocol_client_for_channel(request.channel_id) as client:
        await client.login(request.email, request.password)
        if request.verification_email:
            await client.verify_identity(request.verification_email, provider)
        data = await client.add_recovery_email(request.recovery_email, provider)
    return ApiResponse(success=True, data=data, message="恢复邮箱绑定完成")


@router.post("/api/outlook/protocol/replace")
@handle_exceptions("替换 Outlook 恢复邮箱")
async def replace_protocol_recovery_email(
    admin: AdminUser,
    db: DbManager,
    request: ProtocolReplaceRequest,
) -> ApiResponse:
    _ensure_protocol_enabled()
    if request.queue:
        await _ensure_login_account(db, request.email, request.password)
        resource = await _prepare_resource(
            db,
            target_email=request.email,
            address=request.new_email,
            channel_id=request.channel_id,
            static_code=request.static_code,
        )
        task_id = await db.create_protocol_task(
            task_type="rebind_secondary",
            target_email=request.email,
            old_email=request.old_email.strip(),
            new_email=str(resource["address"]),
            verification_email=(request.verification_email or "").strip(),
            channel_id=request.channel_id,
            resource_id=int(resource["id"]),
            status="pending",
        )
        await add_task_step(
            task_id,
            "queued",
            status="success",
            detail=json.dumps(
                {
                    "task_type": "rebind_secondary",
                    "old_email": request.old_email,
                    "resource": resource["address"],
                    "queued_by": admin,
                },
                ensure_ascii=False,
            ),
        )
        publish_task_event(
            task_id,
            "queued",
            {
                "task_type": "rebind_secondary",
                "old_email": request.old_email,
                "resource": resource["address"],
                "queued_by": admin,
            },
        )
        protocol_rebind_secondary.delay(task_id)
        return ApiResponse(
            success=True,
            data={
                "task_id": task_id,
                "status": "pending",
                "resource_id": int(resource["id"]),
                "resource_address": resource["address"],
            },
            message="恢复邮箱替换任务已创建",
        )

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
