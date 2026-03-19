import logging

from fastapi import APIRouter

from ..core.decorators import handle_exceptions
from ..core.exceptions import (
    AuthenticationError,
    AuthorizationError,
    ExternalServiceError,
    ResourceNotFoundError,
    ServiceUnavailableError,
    ValidationError,
)
from ..dependencies import AdminUser, DbManager
from ..models import ApiResponse
from ..schemas.outlook_accounts import (
    BatchRefreshRequest,
    EmailAuthMethodCreateRequest,
    EmailAuthMethodUpdateRequest,
    MailboxSettingsUpdateRequest,
    PasswordChangeRequest,
    PhoneAuthMethodCreateRequest,
    ProfileUpdateRequest,
    RegionalSettingsUpdateRequest,
    RiskDismissRequest,
)
from ..services.outlook.graph import (
    GraphAPIError,
    add_email_auth_method,
    add_phone_method,
    change_password,
    delete_email_auth_method,
    delete_software_oath_method,
    dismiss_risky_user,
    ensure_graph_operation_ready,
    ensure_graph_capability,
    get_auth_methods_bundle,
    get_mailbox_settings,
    get_regional_settings,
    get_user_profile,
    list_email_auth_methods,
    list_phone_methods,
    list_risky_users,
    list_software_oath_methods,
    revoke_sessions,
    update_email_auth_method,
    update_mailbox_settings,
    update_regional_settings,
    update_user_profile,
)
from ..services.outlook.graph_token_service import (
    batch_refresh_account_tokens,
    refresh_account_token,
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Outlook账户管理"])


def _raise_graph_error(exc: GraphAPIError, email: str | None = None) -> None:
    if exc.status == 401:
        raise AuthenticationError(exc.message)
    if exc.status == 403:
        raise AuthorizationError(exc.message)
    if exc.status == 404:
        raise ResourceNotFoundError(
            message=exc.message,
            resource_type="outlook_account" if email else "graph_resource",
            resource_id=email,
        )
    if exc.status in (422, 400):
        raise ValidationError(exc.message)
    if exc.status in (503, 504):
        raise ServiceUnavailableError(exc.message)
    raise ExternalServiceError(exc.message, service_name="Microsoft Graph")


async def _build_account_view(db, account: dict) -> dict:
    email = account["email"]
    token = await db.get_latest_active_oauth_token(email)
    capabilities = await db.get_account_capabilities(email)
    return {
        **account,
        "token": token,
        "capabilities": capabilities,
    }


@router.get("/api/outlook/accounts")
@handle_exceptions("获取 Outlook 账户列表")
async def list_outlook_accounts(
    admin: AdminUser,
    db: DbManager,
    status: str | None = None,
    account_type: str | None = None,
    limit: int = 100,
    offset: int = 0,
) -> ApiResponse:
    ensure_graph_capability("", "graph")
    accounts = await db.list_outlook_accounts(
        status=status,
        account_type=account_type,
        limit=limit,
        offset=offset,
    )
    items = [await _build_account_view(db, account) for account in accounts]
    total = await db.count_outlook_accounts(status=status, account_type=account_type)
    return ApiResponse(success=True, data={"items": items, "total": total})


@router.post("/api/outlook/accounts/batch-refresh")
@handle_exceptions("批量刷新 Outlook Token")
async def batch_refresh_outlook_tokens(
    admin: AdminUser,
    request: BatchRefreshRequest,
) -> ApiResponse:
    ensure_graph_capability("", "graph")
    summary = await batch_refresh_account_tokens(
        emails=request.emails or None,
        limit=request.limit,
        offset=request.offset,
        concurrency=request.concurrency,
    )
    return ApiResponse(success=True, data=summary, message="批量刷新完成")


@router.get("/api/outlook/accounts/{email}")
@handle_exceptions("获取 Outlook 账户详情")
async def get_outlook_account_detail(
    email: str,
    admin: AdminUser,
    db: DbManager,
) -> ApiResponse:
    ensure_graph_capability(email, "graph")
    account = await db.get_outlook_account(email)
    if not account:
        raise ResourceNotFoundError("Outlook 账户不存在", resource_type="outlook_account", resource_id=email)
    detail = await _build_account_view(db, account)
    detail["profile_cache"] = await db.get_account_profile_cache(email)
    detail["security_methods_snapshot"] = await db.list_account_security_method_snapshots(email)
    detail["recent_operations"] = await db.list_account_operation_audits(email=email, limit=20)
    return ApiResponse(success=True, data=detail)


@router.post("/api/outlook/accounts/{email}/refresh-token")
@handle_exceptions("刷新 Outlook Token")
async def refresh_outlook_token(
    email: str,
    admin: AdminUser,
) -> ApiResponse:
    ensure_graph_capability(email, "graph")
    try:
        token = await refresh_account_token(email)
    except GraphAPIError as exc:
        _raise_graph_error(exc, email)
    return ApiResponse(success=True, data=token, message="Token 刷新成功")


@router.get("/api/outlook/accounts/{email}/profile")
@handle_exceptions("获取 Outlook 用户资料")
async def get_outlook_profile(email: str, admin: AdminUser, refresh: bool = False) -> ApiResponse:
    await ensure_graph_operation_ready(email)
    try:
        data = await get_user_profile(email, force_refresh=refresh)
    except GraphAPIError as exc:
        _raise_graph_error(exc, email)
    return ApiResponse(success=True, data=data)


@router.patch("/api/outlook/accounts/{email}/profile")
@handle_exceptions("更新 Outlook 用户资料")
async def patch_outlook_profile(
    email: str,
    admin: AdminUser,
    request: ProfileUpdateRequest,
) -> ApiResponse:
    await ensure_graph_operation_ready(email)
    try:
        data = await update_user_profile(email, request.updates)
    except GraphAPIError as exc:
        _raise_graph_error(exc, email)
    return ApiResponse(success=True, data=data, message="用户资料已更新")


@router.post("/api/outlook/accounts/{email}/change-password")
@handle_exceptions("修改 Outlook 密码")
async def post_change_password(
    email: str,
    admin: AdminUser,
    request: PasswordChangeRequest,
) -> ApiResponse:
    await ensure_graph_operation_ready(email)
    try:
        data = await change_password(email, request.current_password, request.new_password)
    except GraphAPIError as exc:
        _raise_graph_error(exc, email)
    return ApiResponse(success=True, data=data, message="密码已修改")


@router.get("/api/outlook/accounts/{email}/auth-methods")
@handle_exceptions("获取 Outlook 验证方式")
async def get_outlook_auth_methods(email: str, admin: AdminUser) -> ApiResponse:
    await ensure_graph_operation_ready(email)
    try:
        data = await get_auth_methods_bundle(email)
    except GraphAPIError as exc:
        _raise_graph_error(exc, email)
    return ApiResponse(success=True, data=data)


@router.get("/api/outlook/accounts/{email}/auth-methods/email")
@handle_exceptions("获取 Outlook 恢复邮箱")
async def get_outlook_email_methods(email: str, admin: AdminUser) -> ApiResponse:
    await ensure_graph_operation_ready(email)
    try:
        data = await list_email_auth_methods(email)
    except GraphAPIError as exc:
        _raise_graph_error(exc, email)
    return ApiResponse(success=True, data=data)


@router.post("/api/outlook/accounts/{email}/auth-methods/email")
@handle_exceptions("添加 Outlook 恢复邮箱")
async def create_outlook_email_method(
    email: str,
    admin: AdminUser,
    request: EmailAuthMethodCreateRequest,
) -> ApiResponse:
    await ensure_graph_operation_ready(email)
    try:
        data = await add_email_auth_method(email, request.recovery_email)
    except GraphAPIError as exc:
        _raise_graph_error(exc, email)
    return ApiResponse(success=True, data=data, message="恢复邮箱已添加")


@router.put("/api/outlook/accounts/{email}/auth-methods/email/{method_id}")
@handle_exceptions("更新 Outlook 恢复邮箱")
async def put_outlook_email_method(
    email: str,
    method_id: str,
    admin: AdminUser,
    request: EmailAuthMethodUpdateRequest,
) -> ApiResponse:
    await ensure_graph_operation_ready(email)
    try:
        data = await update_email_auth_method(email, method_id, request.new_email)
    except GraphAPIError as exc:
        _raise_graph_error(exc, email)
    return ApiResponse(success=True, data=data, message="恢复邮箱已更新")


@router.delete("/api/outlook/accounts/{email}/auth-methods/email/{method_id}")
@handle_exceptions("删除 Outlook 恢复邮箱")
async def remove_outlook_email_method(
    email: str,
    method_id: str,
    admin: AdminUser,
) -> ApiResponse:
    await ensure_graph_operation_ready(email)
    try:
        data = await delete_email_auth_method(email, method_id)
    except GraphAPIError as exc:
        _raise_graph_error(exc, email)
    return ApiResponse(success=True, data=data, message="恢复邮箱已删除")


@router.get("/api/outlook/accounts/{email}/auth-methods/totp")
@handle_exceptions("获取 Outlook TOTP")
async def get_outlook_totp_methods(email: str, admin: AdminUser) -> ApiResponse:
    await ensure_graph_operation_ready(email)
    try:
        data = await list_software_oath_methods(email)
    except GraphAPIError as exc:
        _raise_graph_error(exc, email)
    return ApiResponse(success=True, data=data)


@router.delete("/api/outlook/accounts/{email}/auth-methods/totp/{method_id}")
@handle_exceptions("删除 Outlook TOTP")
async def remove_outlook_totp_method(
    email: str,
    method_id: str,
    admin: AdminUser,
) -> ApiResponse:
    await ensure_graph_operation_ready(email)
    try:
        data = await delete_software_oath_method(email, method_id)
    except GraphAPIError as exc:
        _raise_graph_error(exc, email)
    return ApiResponse(success=True, data=data, message="TOTP 已删除")


@router.get("/api/outlook/accounts/{email}/auth-methods/phone")
@handle_exceptions("获取 Outlook 手机号验证方式")
async def get_outlook_phone_methods(email: str, admin: AdminUser) -> ApiResponse:
    await ensure_graph_operation_ready(email)
    try:
        data = await list_phone_methods(email)
    except GraphAPIError as exc:
        _raise_graph_error(exc, email)
    return ApiResponse(success=True, data=data)


@router.post("/api/outlook/accounts/{email}/auth-methods/phone")
@handle_exceptions("添加 Outlook 手机号验证方式")
async def create_outlook_phone_method(
    email: str,
    admin: AdminUser,
    request: PhoneAuthMethodCreateRequest,
) -> ApiResponse:
    await ensure_graph_operation_ready(email)
    try:
        data = await add_phone_method(email, request.phone_number, request.phone_type)
    except GraphAPIError as exc:
        _raise_graph_error(exc, email)
    return ApiResponse(success=True, data=data, message="手机号验证方式已添加")


@router.post("/api/outlook/accounts/{email}/revoke-sessions")
@handle_exceptions("撤销 Outlook 会话")
async def post_revoke_sessions(email: str, admin: AdminUser) -> ApiResponse:
    await ensure_graph_operation_ready(email)
    try:
        data = await revoke_sessions(email)
    except GraphAPIError as exc:
        _raise_graph_error(exc, email)
    return ApiResponse(success=True, data=data, message="会话已撤销")


@router.get("/api/outlook/accounts/{email}/risky-users")
@handle_exceptions("获取 Outlook 风险用户")
async def get_outlook_risky_users(email: str, admin: AdminUser) -> ApiResponse:
    await ensure_graph_operation_ready(email)
    try:
        data = await list_risky_users(email)
    except GraphAPIError as exc:
        _raise_graph_error(exc, email)
    return ApiResponse(success=True, data=data)


@router.post("/api/outlook/accounts/{email}/dismiss-risk")
@handle_exceptions("解除 Outlook 风险用户状态")
async def post_dismiss_risk(
    email: str,
    admin: AdminUser,
    request: RiskDismissRequest,
) -> ApiResponse:
    await ensure_graph_operation_ready(email)
    try:
        data = await dismiss_risky_user(email, request.user_id)
    except GraphAPIError as exc:
        _raise_graph_error(exc, email)
    return ApiResponse(success=True, data=data, message="风险状态已解除")


@router.get("/api/outlook/accounts/{email}/regional-settings")
@handle_exceptions("获取 Outlook 区域设置")
async def get_outlook_regional_settings(email: str, admin: AdminUser) -> ApiResponse:
    await ensure_graph_operation_ready(email)
    try:
        data = await get_regional_settings(email)
    except GraphAPIError as exc:
        _raise_graph_error(exc, email)
    return ApiResponse(success=True, data=data)


@router.patch("/api/outlook/accounts/{email}/regional-settings")
@handle_exceptions("更新 Outlook 区域设置")
async def patch_outlook_regional_settings(
    email: str,
    admin: AdminUser,
    request: RegionalSettingsUpdateRequest,
) -> ApiResponse:
    await ensure_graph_operation_ready(email)
    try:
        data = await update_regional_settings(email, request.updates)
    except GraphAPIError as exc:
        _raise_graph_error(exc, email)
    return ApiResponse(success=True, data=data, message="区域设置已更新")


@router.get("/api/outlook/accounts/{email}/mailbox-settings")
@handle_exceptions("获取 Outlook 邮箱设置")
async def get_outlook_mailbox_settings(email: str, admin: AdminUser) -> ApiResponse:
    await ensure_graph_operation_ready(email)
    try:
        data = await get_mailbox_settings(email)
    except GraphAPIError as exc:
        _raise_graph_error(exc, email)
    return ApiResponse(success=True, data=data)


@router.patch("/api/outlook/accounts/{email}/mailbox-settings")
@handle_exceptions("更新 Outlook 邮箱设置")
async def patch_outlook_mailbox_settings(
    email: str,
    admin: AdminUser,
    request: MailboxSettingsUpdateRequest,
) -> ApiResponse:
    await ensure_graph_operation_ready(email)
    try:
        data = await update_mailbox_settings(email, request.updates)
    except GraphAPIError as exc:
        _raise_graph_error(exc, email)
    return ApiResponse(success=True, data=data, message="邮箱设置已更新")
