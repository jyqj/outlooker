from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Tuple

from ..database import db_manager, looks_like_guid
from ..models import ImportAccountData, ImportResult
from ..security import encrypt_if_needed
from ..settings import get_settings
from .account_utils import _normalize_email, _validate_account_info
from .constants import VALID_MERGE_MODES
from .email_service import email_manager

_settings = get_settings()
CLIENT_ID = (_settings.client_id or "").strip()


@dataclass
class ImportStats:
    """导入统计信息"""

    added: int = 0
    updated: int = 0
    skipped: int = 0
    errors: int = 0
    details: List[Dict[str, str]] = field(default_factory=list)

    def record(self, action: str, detail: Dict[str, str]) -> None:
        if action == "added":
            self.added += 1
        elif action == "updated":
            self.updated += 1
        elif action == "skipped":
            self.skipped += 1
        elif action == "error":
            self.errors += 1
        self.details.append(detail)


def _prepare_and_validate_accounts(
    accounts: List[ImportAccountData]
) -> Tuple[Dict[str, Dict[str, str]], List[Dict[str, str]], int]:
    """准备并验证账户数据"""
    prepared: Dict[str, Dict[str, str]] = {}
    error_details: List[Dict[str, str]] = []
    error_count = 0

    for idx, account in enumerate(accounts, 1):
        original_email = (account.email or "").strip()
        normalized_email = _normalize_email(original_email)
        refresh_token = (account.refresh_token or "").strip()

        if not normalized_email:
            error_count += 1
            error_details.append(
                {
                    "action": "error",
                    "email": original_email,
                    "message": f"第{idx}条缺少有效邮箱",
                }
            )
            continue

        if not refresh_token:
            error_count += 1
            email_display = original_email or normalized_email
            error_details.append(
                {
                    "action": "error",
                    "email": email_display,
                    "message": f"{email_display} 缺少 refresh_token",
                }
            )
            continue

        entry_email = original_email or normalized_email
        password_plain = (account.password or "").strip()
        candidate_client_id = (account.client_id or "").strip()
        if candidate_client_id and not looks_like_guid(candidate_client_id):
            candidate_client_id = ""
        prepared[normalized_email] = {
            "email": entry_email,
            "password": encrypt_if_needed(password_plain) if password_plain else "",
            "client_id": (candidate_client_id or CLIENT_ID).strip() or CLIENT_ID,
            "refresh_token": encrypt_if_needed(refresh_token),
        }

        validation_errors = _validate_account_info(entry_email, prepared[normalized_email])
        if validation_errors:
            error_count += 1
            error_details.append(
                {
                    "action": "error",
                    "email": entry_email,
                    "message": "; ".join(validation_errors),
                }
            )
            prepared.pop(normalized_email, None)
            continue

    return prepared, error_details, error_count


async def _handle_replace_mode(
    prepared: Dict[str, Dict[str, str]],
    total_count: int,
    error_count: int,
    error_details: List[Dict[str, str]],
) -> ImportResult:
    """处理 replace 模式的账户导入"""
    valid_accounts = {
        info["email"]: {
            "password": info["password"],
            "client_id": info["client_id"],
            "refresh_token": info["refresh_token"],
        }
        for info in prepared.values()
    }

    if not valid_accounts:
        message = "没有有效账户，无法执行替换"
        return ImportResult(
            success=False,
            total_count=total_count,
            added_count=0,
            updated_count=0,
            skipped_count=0,
            error_count=error_count or total_count,
            details=error_details,
            message=message,
        )

    replaced = await db_manager.replace_all_accounts(valid_accounts)
    if replaced:
        added_count = len(valid_accounts)
        await email_manager.invalidate_accounts_cache()
        message = f"替换完成：共导入 {added_count} 条账户"
        return ImportResult(
            success=True,
            total_count=total_count,
            added_count=added_count,
            updated_count=0,
            skipped_count=0,
            error_count=error_count,
            details=error_details,
            message=message,
        )

    error_count = max(error_count, total_count or len(valid_accounts))
    message = "替换账户失败"
    return ImportResult(
        success=False,
        total_count=total_count,
        added_count=0,
        updated_count=0,
        skipped_count=0,
        error_count=error_count,
        details=error_details,
        message=message,
    )


async def _process_single_account_update_mode(
    normalized_email: str,
    info: Dict[str, str],
    lookup_existing: Dict[str, str],
    merge_mode: str,
) -> Tuple[str, Dict[str, str]]:
    """处理单个账户的 update/skip/add 逻辑"""
    email_to_use = lookup_existing.get(normalized_email, info["email"] or normalized_email)
    payload = {
        "password": info["password"],
        "client_id": info["client_id"],
        "refresh_token": info["refresh_token"],
    }

    if normalized_email in lookup_existing:
        if merge_mode == "skip":
            return "skipped", {
                "action": "skipped",
                "email": info["email"],
                "message": "已存在，按照 skip 策略跳过",
            }

        updated = await db_manager.update_account(
            lookup_existing[normalized_email],
            password=payload["password"],
            client_id=payload["client_id"],
            refresh_token=payload["refresh_token"],
        )
        if updated:
            return "updated", {
                "action": "updated",
                "email": lookup_existing[normalized_email],
                "message": "账户已更新",
            }
        return "error", {
            "action": "error",
            "email": lookup_existing[normalized_email],
            "message": "更新账户失败",
        }

    added = await db_manager.add_account(
        email_to_use,
        password=payload["password"],
        client_id=payload["client_id"],
        refresh_token=payload["refresh_token"],
    )
    if added:
        return "added", {
            "action": "added",
            "email": email_to_use,
            "message": "账户已添加",
        }
    return "error", {
        "action": "error",
        "email": email_to_use,
        "message": "添加账户失败",
    }


async def _handle_update_skip_mode(
    prepared: Dict[str, Dict[str, str]],
    merge_mode: str,
) -> ImportStats:
    """处理 update/skip 模式的账户导入"""
    stats = ImportStats()

    existing_accounts = await db_manager.get_all_accounts()
    lookup_existing = {addr.lower(): addr for addr in existing_accounts.keys()}

    for normalized_email, info in prepared.items():
        action, detail = await _process_single_account_update_mode(
            normalized_email, info, lookup_existing, merge_mode
        )
        stats.record(action, detail)

    return stats


def _build_import_result(
    total_count: int,
    added_count: int,
    updated_count: int,
    skipped_count: int,
    error_count: int,
    details: List[Dict[str, str]],
) -> ImportResult:
    message = (
        f"导入完成：新增 {added_count}，更新 {updated_count}，"
        f"跳过 {skipped_count}，错误 {error_count}"
    )

    made_changes = (added_count + updated_count) > 0
    success = True if made_changes or error_count == 0 else False

    return ImportResult(
        success=success,
        total_count=total_count,
        added_count=added_count,
        updated_count=updated_count,
        skipped_count=skipped_count,
        error_count=error_count,
        details=details,
        message=message,
    )


async def merge_accounts_data_to_db(
    accounts: List[ImportAccountData],
    merge_mode: str = "update",
) -> ImportResult:
    """根据不同模式合并账户数据"""
    merge_mode = (merge_mode or "update").lower()
    if merge_mode not in VALID_MERGE_MODES:
        merge_mode = "update"

    total_count = len(accounts)
    prepared, error_details, error_count = _prepare_and_validate_accounts(accounts)

    if merge_mode == "replace":
        return await _handle_replace_mode(prepared, total_count, error_count, error_details)

    stats = await _handle_update_skip_mode(prepared, merge_mode)
    error_count += stats.errors
    all_details = error_details + stats.details

    if stats.added or stats.updated:
        await email_manager.invalidate_accounts_cache()

    return _build_import_result(
        total_count, stats.added, stats.updated, stats.skipped, error_count, all_details
    )
