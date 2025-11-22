from fastapi import APIRouter, HTTPException, Header, Depends
from fastapi.responses import PlainTextResponse
from typing import Optional, Dict, List, Union
from datetime import datetime

from ..models import ApiResponse, AccountTagRequest, AccountCredentials, ImportAccountData, ImportRequest, ParseImportTextRequest
from ..config import CLIENT_ID, logger
from ..jwt_auth import get_current_admin
from ..services import (
    load_accounts_config, merge_accounts_data_to_db, 
    email_manager, db_manager, parse_account_line
)
from ..utils.pagination import paginate_items

router = APIRouter(tags=["账户管理"])
DEFAULT_ACCOUNT_PAGE_SIZE = 10
MAX_ACCOUNT_PAGE_SIZE = 100


def _mask_secret(value: str) -> str:
    if not value:
        return ""
    plain = value
    if len(plain) <= 4:
        return "*" * len(plain)
    return f"{plain[:2]}***{plain[-2:]}"

@router.get("/api/accounts")
async def get_accounts(authorization: Optional[str] = Header(None)) -> ApiResponse:
    """获取所有账户列表（需要管理员认证）"""
    try:
        _ = get_current_admin(authorization)
        accounts = await load_accounts_config()
        account_list = [
            {
                "email": email,
                # 来自数据库的账户会包含使用状态字段；文件来源则默认为未使用
                "is_used": bool(info.get("is_used")),
                "last_used_at": info.get("last_used_at"),
            }
            for email, info in accounts.items()
        ]
        return ApiResponse(success=True, data=account_list, message=f"共 {len(account_list)} 个账户")
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"获取账户列表失败: {e}")
        return ApiResponse(success=False, message="获取账户列表失败")

@router.get("/api/accounts/paged")
async def get_accounts_paged(
    q: Optional[str] = None,
    page: int = 1,
    page_size: int = DEFAULT_ACCOUNT_PAGE_SIZE,
    authorization: Optional[str] = Header(None)
) -> ApiResponse:
    """分页与搜索账户列表（需要管理员认证）"""
    try:
        _ = get_current_admin(authorization)

        accounts_dict = await load_accounts_config()
        emails = sorted(accounts_dict.keys())

        if q:
            q_lower = q.strip().lower()
            emails = [e for e in emails if q_lower in e.lower()]

        # 统一使用通用分页工具，保持逻辑一致性
        items_page, total = paginate_items(
            emails,
            max(1, page),
            max(1, min(MAX_ACCOUNT_PAGE_SIZE, page_size)),
        )

        # 为每个账户附加使用状态，便于前端展示“已使用/未使用”
        items = []
        for e in items_page:
            info = accounts_dict.get(e, {}) or {}
            items.append(
                {
                    "email": e,
                    "is_used": bool(info.get("is_used")),
                    "last_used_at": info.get("last_used_at"),
                }
            )

        return ApiResponse(
            success=True,
            data={
                "items": items,
                "total": total,
                "page": page,
                "page_size": page_size
            },
            message=f"共 {total} 个账户"
        )
    except Exception as e:
        logger.error(f"分页获取账户列表失败: {e}")
        return ApiResponse(success=False, message="获取账户列表失败")

@router.get("/api/accounts/tags", tags=["标签管理"])
async def get_accounts_tags(authorization: Optional[str] = Header(None)) -> ApiResponse:
    """获取所有标签和账户-标签映射（需要管理员认证）"""
    try:
        _ = get_current_admin(authorization)

        tags = await db_manager.get_all_tags()
        accounts_map = await db_manager.get_accounts_with_tags()
        return ApiResponse(success=True, data={"tags": tags, "accounts": accounts_map})
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"获取账户标签失败: {e}")
        return ApiResponse(success=False, message="获取账户标签失败")

@router.get("/api/account/{email}/tags", tags=["标签管理"])
async def get_account_tags(email: str, authorization: Optional[str] = Header(None)) -> ApiResponse:
    """获取指定账户的标签（需要管理员认证）"""
    try:
        _ = get_current_admin(authorization)

        tags = await db_manager.get_account_tags(email)
        return ApiResponse(success=True, data={"email": email, "tags": tags})
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"获取账户标签失败({email}): {e}")
        return ApiResponse(success=False, message="获取账户标签失败")

@router.post("/api/account/{email}/tags", tags=["标签管理"])
async def set_account_tags(
    email: str,
    request: AccountTagRequest,
    authorization: Optional[str] = Header(None)
) -> ApiResponse:
    """设置指定账户的标签（需要管理员认证）"""
    try:
        # 需要管理认证
        _ = get_current_admin(authorization)

        # 保护：路径中的邮箱与请求体邮箱需一致（若请求体提供）
        if request.email and request.email != email:
            return ApiResponse(success=False, message="邮箱不一致")

        # 去重并清理空白
        cleaned_tags = []
        seen = set()
        for t in (request.tags or []):
            tag = (t or "").strip()
            if not tag:
                continue
            if tag not in seen:
                seen.add(tag)
                cleaned_tags.append(tag)

        ok = await db_manager.set_account_tags(email, cleaned_tags)
        if ok:
            return ApiResponse(success=True, message="标签已保存", data={"email": email, "tags": cleaned_tags})
        return ApiResponse(success=False, message="保存标签失败")
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"保存账户标签失败({email}): {e}")
        return ApiResponse(success=False, message="保存标签失败")

@router.post("/api/import")
async def import_accounts_dict(request: ImportRequest, authorization: Optional[str] = Header(None)) -> dict:
    """批量导入邮箱账户（需要管理员认证）

    使用 Pydantic 模型验证请求数据,确保数据格式正确

    请求体:
    {
        "accounts": [
            {
                "email": "user@example.com",
                "password": "optional",
                "client_id": "optional",
                "refresh_token": "required"
            }
        ],
        "merge_mode": "update"  // "update", "skip", "replace"
    }
    """
    try:
        _ = get_current_admin(authorization)

        logger.info(f"收到导入请求，账户数量: {len(request.accounts)}, 合并模式: {request.merge_mode}")

        # Pydantic 已经验证了数据格式,直接使用
        accounts = request.accounts
        merge_mode = request.merge_mode

        # 直接合并到数据库
        result = await merge_accounts_data_to_db(accounts, merge_mode)
        
        # 清除账户缓存以便重新加载
        if result.success and (result.added_count > 0 or result.updated_count > 0):
            await email_manager.invalidate_accounts_cache()
        
        return {
            "success": result.success,
            "total_count": result.total_count,
            "added_count": result.added_count,
            "updated_count": result.updated_count,
            "skipped_count": result.skipped_count,
            "error_count": result.error_count,
            "details": result.details,
            "message": result.message
        }
        
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.exception(f"导入账户失败: {e}")
        return {
            "success": False,
            "total_count": len(request.accounts),
            "added_count": 0,
            "updated_count": 0,
            "skipped_count": 0,
            "error_count": len(request.accounts),
            "details": [{"action": "error", "message": f"系统错误: {str(e)}"}],
            "message": f"导入失败: {str(e)}"
        }

@router.post("/api/parse-import-text")
async def parse_import_text(request: ParseImportTextRequest, authorization: Optional[str] = Header(None)) -> ApiResponse:
    """解析导入文本格式数据（需要管理员认证）

    使用 Pydantic 模型验证请求数据

    请求体:
    {
        "text": "email----password----refresh_token----client_id\\n..."
    }
    """
    try:
        _ = get_current_admin(authorization)

        import_text = request.text.strip()
        if not import_text:
            return ApiResponse(success=False, message="请提供要导入的文本数据")

        accounts = []
        errors = []

        lines = import_text.split('\n')
        for line_num, line in enumerate(lines, 1):
            try:
                parsed = parse_account_line(line)
                if not parsed:
                    continue

                email, info = parsed
                accounts.append({
                    "email": email,
                    "password": info["password"],
                    "client_id": info["client_id"],
                    "refresh_token": info["refresh_token"]
                })
            except ValueError as e:
                errors.append(f"第{line_num}行格式错误：{str(e)}")
            except Exception as e:
                errors.append(f"第{line_num}行解析失败：{str(e)}")

        result_data = {
            "accounts": accounts,
            "parsed_count": len(accounts),
            "error_count": len(errors),
            "errors": errors
        }

        if errors:
            return ApiResponse(
                success=True,
                data=result_data,
                message=f"解析完成：成功 {len(accounts)} 条，错误 {len(errors)} 条"
            )
        else:
            return ApiResponse(
                success=True,
                data=result_data,
                message=f"解析成功：共 {len(accounts)} 条账户数据"
            )

    except HTTPException as e:
        raise e
    except Exception as e:
        logger.exception(f"解析导入文本失败: {e}")
        return ApiResponse(success=False, message=f"解析失败: {str(e)}")

@router.get("/api/export")
async def export_accounts_public(format: str = "txt", authorization: Optional[str] = Header(None)):
    """导出账户配置（需要管理员认证）"""
    try:
        _ = get_current_admin(authorization)

        accounts = await load_accounts_config()
        
        if not accounts:
            raise HTTPException(status_code=404, detail="暂无账户数据")
        
        export_lines = []
        export_lines.append("# Outlook邮件系统账号配置文件")
        export_lines.append(f"# 导出时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        export_lines.append("# 格式: 邮箱----密码----refresh_token----client_id")
        export_lines.append("# 注意：请妥善保管此文件，包含敏感信息")
        export_lines.append("")
        
        for email, account_info in accounts.items():
            password = account_info.get('password', '')
            refresh_token = account_info.get('refresh_token', '')
            client_id = account_info.get('client_id', CLIENT_ID)
            line = f"{email}----{password}----{refresh_token}----{client_id}"
            export_lines.append(line)
        
        export_content = "\n".join(export_lines)
        filename = f"outlook_accounts_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        
        return PlainTextResponse(
            content=export_content,
            headers={
                "Content-Disposition": f"attachment; filename={filename}",
                "Content-Type": "text/plain; charset=utf-8"
            }
        )
        
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.exception(f"导出账户配置失败: {e}")
        raise HTTPException(status_code=500, detail=f"导出失败: {str(e)}")
@router.post("/api/accounts", tags=["账户管理"])
async def create_account(
    request: AccountCredentials, authorization: Optional[str] = Header(None)
) -> ApiResponse:
    """创建单个账户"""
    get_current_admin(authorization)
    success = await db_manager.add_account(
        request.email,
        password=request.password,
        client_id=request.client_id or CLIENT_ID,
        refresh_token=request.refresh_token,
    )
    if not success:
        return ApiResponse(success=False, message="账户已存在或创建失败")

    await email_manager.invalidate_accounts_cache()
    return ApiResponse(success=True, data={"email": request.email}, message="账户已创建")


@router.put("/api/account/{email}", tags=["账户管理"])
async def update_account(
    email: str,
    request: AccountCredentials,
    authorization: Optional[str] = Header(None),
) -> ApiResponse:
    """更新指定账户"""
    get_current_admin(authorization)

    if request.email and request.email != email:
        return ApiResponse(success=False, message="邮箱与路径参数不一致")

    success = await db_manager.update_account(
        email,
        password=request.password,
        client_id=request.client_id or CLIENT_ID,
        refresh_token=request.refresh_token,
    )
    if not success:
        return ApiResponse(success=False, message="账户不存在或更新失败")

    await email_manager.invalidate_accounts_cache()
    return ApiResponse(success=True, message="账户已更新", data={"email": email})


@router.delete("/api/account/{email}", tags=["账户管理"])
async def delete_account(
    email: str, authorization: Optional[str] = Header(None)
) -> ApiResponse:
    """删除账户"""
    get_current_admin(authorization)
    deleted = await db_manager.delete_account(email)
    if not deleted:
        return ApiResponse(success=False, message="账户不存在或删除失败")

    await email_manager.invalidate_accounts_cache()
    return ApiResponse(success=True, message="账户已删除", data={"email": email})


@router.get("/api/account/{email}", tags=["账户管理"])
async def get_account_detail(
    email: str, authorization: Optional[str] = Header(None)
) -> ApiResponse:
    """获取单个账户详情（敏感字段已脱敏）"""
    get_current_admin(authorization)
    account = await db_manager.get_account(email)
    if not account:
        raise HTTPException(status_code=404, detail="账户不存在")

    return ApiResponse(
        success=True,
        data={
            "email": email,
            "client_id": account["client_id"],
            "has_password": bool(account["password"]),
            "has_refresh_token": bool(account["refresh_token"]),
            "password_preview": _mask_secret(account["password"]),
            "refresh_token_preview": _mask_secret(account["refresh_token"]),
            "is_used": bool(account.get("is_used")),
            "last_used_at": account.get("last_used_at"),
        },
    )
