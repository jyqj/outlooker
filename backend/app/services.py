#!/usr/bin/env python3
"""业务服务层

集中管理账户加载、邮件获取、系统配置等能力，提供给路由层复用。
"""

from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from fastapi import HTTPException

from .config import (
    CLIENT_ID,
    DEFAULT_EMAIL_LIMIT,
    INBOX_FOLDER_NAME,
    MAX_EMAIL_LIMIT as CONFIG_MAX_EMAIL_LIMIT,
    logger,
)
from .messages import ERROR_EMAIL_NOT_CONFIGURED, ERROR_EMAIL_NOT_PROVIDED
from .database import db_manager, looks_like_guid
from .imap_client import IMAPEmailClient
from .models import ImportAccountData, ImportResult
from .security import encrypt_if_needed, decrypt_if_needed
from .settings import get_settings

settings = get_settings()
PROJECT_ROOT = Path(__file__).resolve().parents[2]
CONFIG_DIR = PROJECT_ROOT / "backend" / "configs"
ACCOUNTS_CONFIG_FILES = [
    CONFIG_DIR / "config.txt",
    CONFIG_DIR / "accounts.txt",
]
SYSTEM_CONFIG_FILE = CONFIG_DIR / "system_config.json"
SYSTEM_CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
SYSTEM_CONFIG_DEFAULTS: Dict[str, Any] = {
    "email_limit": DEFAULT_EMAIL_LIMIT,
}
VALID_MERGE_MODES = {"update", "skip", "replace"}
MIN_EMAIL_LIMIT = 1
MAX_EMAIL_LIMIT = CONFIG_MAX_EMAIL_LIMIT


_system_config_lock = asyncio.Lock()


def _normalize_email(email: str) -> str:
    return (email or "").strip().lower()


def _validate_account_info(email: str, account_info: Dict[str, str]) -> List[str]:
    """基础字段校验，返回问题列表"""
    errors: List[str] = []

    refresh_token = (account_info.get("refresh_token") or "").strip()
    if not refresh_token:
        errors.append(f"{email} 缺少 refresh_token")

    client_id = (account_info.get("client_id") or "").strip()
    if client_id and not looks_like_guid(client_id):
        errors.append(f"{email} 的 client_id 格式不正确")

    return errors


def parse_account_line(line: str) -> Optional[Tuple[str, Dict[str, str]]]:
    """解析配置文件中的账户行 (公共函数)"""
    raw = (line or "").strip()
    if not raw or raw.startswith("#"):
        return None

    parts = [p.strip() for p in raw.split("----")]
    if len(parts) >= 4:
        email, password, refresh_token, client_id = parts[:4]
    elif len(parts) == 2:
        email, refresh_token = parts
        password = ""
        client_id = CLIENT_ID
    else:
        raise ValueError("格式需要2或4个字段")

    email = email.strip()
    refresh_token = refresh_token.strip()
    password = password.strip()
    client_id = client_id.strip() or CLIENT_ID

    if not email:
        raise ValueError("邮箱不能为空")
    if not refresh_token:
        raise ValueError(f"{email}: 缺少 refresh_token")

    return email, {
        "password": password,
        "client_id": client_id,
        "refresh_token": refresh_token,
    }


# 内部别名, 兼容现有测试与旧代码
_parse_account_line = parse_account_line


def _load_accounts_from_files() -> Dict[str, Dict[str, str]]:
    """从本地配置文件加载账户（兼容 config.txt）"""
    accounts: Dict[str, Dict[str, str]] = {}

    for file_path in ACCOUNTS_CONFIG_FILES:
        if not file_path.exists():
            continue

        try:
            with file_path.open("r", encoding="utf-8") as fp:
                for idx, line in enumerate(fp, 1):
                    try:
                        parsed = parse_account_line(line)
                    except ValueError as exc:
                        logger.warning(f"解析 {file_path.name} 第{idx}行失败: {exc}")
                        continue

                    if parsed is None:
                        continue

                    email, info = parsed
                    accounts[email] = info

            if accounts:
                logger.info(f"从 {file_path.name} 加载 {len(accounts)} 个账户")
        except Exception as exc:
            logger.error(f"读取 {file_path} 失败: {exc}", exc_info=True)

    return accounts


def _read_system_config_file() -> Dict[str, Any]:
    if not SYSTEM_CONFIG_FILE.exists():
        return {}

    try:
        with SYSTEM_CONFIG_FILE.open("r", encoding="utf-8") as fp:
            return json.load(fp)
    except Exception as exc:
        logger.warning(f"读取系统配置文件失败: {exc}")
        return {}


async def _write_system_config_file(config: Dict[str, Any]) -> None:
    async with _system_config_lock:
        try:
            with SYSTEM_CONFIG_FILE.open("w", encoding="utf-8") as fp:
                json.dump(config, fp, ensure_ascii=False, indent=2)
        except Exception as exc:
            logger.error(f"写入系统配置文件失败: {exc}", exc_info=True)


def _cast_system_value(key: str, value: Any) -> Any:
    if value is None:
        return value
    if key == "email_limit":
        try:
            limit = int(value)
        except (TypeError, ValueError):
            return SYSTEM_CONFIG_DEFAULTS[key]
        return max(MIN_EMAIL_LIMIT, min(MAX_EMAIL_LIMIT, limit))
    return value


class EmailManager:
    """统一封装邮件获取逻辑和账户缓存"""

    def __init__(self) -> None:
        self._accounts_cache: Optional[Dict[str, Dict[str, str]]] = None
        self._accounts_lock: Optional[asyncio.Lock] = None
        self._accounts_lock_loop: Optional[asyncio.AbstractEventLoop] = None
        self._clients: Dict[str, IMAPEmailClient] = {}
        self._client_tokens: Dict[str, str] = {}
        self._clients_lock: Optional[asyncio.Lock] = None
        self._clients_lock_loop: Optional[asyncio.AbstractEventLoop] = None
        self._accounts_source: str = "unknown"
        self._metrics = {
            "cache_hits": 0,
            "cache_misses": 0,
            "client_reuses": 0,
            "client_creates": 0,
            "db_loads": 0,
            "cache_refreshes": 0,
            "last_cache_refresh_at": None,
        }

    def _get_accounts_lock(self) -> asyncio.Lock:
        current_loop = asyncio.get_running_loop()
        if self._accounts_lock is None or self._accounts_lock_loop is not current_loop:
            self._accounts_lock = asyncio.Lock()
            self._accounts_lock_loop = current_loop
        return self._accounts_lock

    def _get_clients_lock(self) -> asyncio.Lock:
        current_loop = asyncio.get_running_loop()
        if self._clients_lock is None or self._clients_lock_loop is not current_loop:
            self._clients_lock = asyncio.Lock()
            self._clients_lock_loop = current_loop
        return self._clients_lock

    async def load_accounts(self, force_refresh: bool = False) -> Dict[str, Dict[str, str]]:
        if not force_refresh and self._accounts_cache is not None:
            self._metrics["cache_hits"] += 1
            return dict(self._accounts_cache)

        async with self._get_accounts_lock():
            if not force_refresh and self._accounts_cache is not None:
                self._metrics["cache_hits"] += 1
                return dict(self._accounts_cache)

            self._metrics["cache_misses"] += 1
            self._metrics["db_loads"] += 1
            accounts = await db_manager.get_all_accounts()

            if accounts:
                self._accounts_source = "database"
                # 解密数据库中的敏感字段
                for email, info in accounts.items():
                    if info.get("password"):
                        info["password"] = decrypt_if_needed(info["password"])
                    if info.get("refresh_token"):
                        info["refresh_token"] = decrypt_if_needed(info["refresh_token"])
            else:
                logger.warning("数据库为空，从配置文件加载账户（仅用于初始化）")
                accounts = _load_accounts_from_files()
                self._accounts_source = "file" if accounts else "none"

            self._accounts_cache = accounts
            self._metrics["cache_refreshes"] += 1
            self._metrics["last_cache_refresh_at"] = datetime.utcnow().isoformat()
            return dict(accounts)

    async def invalidate_accounts_cache(self) -> None:
        async with self._get_accounts_lock():
            self._accounts_cache = None

    async def _get_account_info(self, email: str) -> Tuple[str, Dict[str, str]]:
        accounts = await self.load_accounts()
        lookup = {addr.lower(): addr for addr in accounts.keys()}
        normalized = _normalize_email(email)
        actual_email = lookup.get(normalized)

        if not actual_email:
            raise HTTPException(status_code=404, detail=ERROR_EMAIL_NOT_CONFIGURED)

        return actual_email, accounts[actual_email]

    async def _get_or_create_client(self, email: str, account_info: Dict[str, str]) -> IMAPEmailClient:
        """复用或创建 IMAP 客户端

        - 若缓存中存在且 refresh_token 未变化则直接复用，避免重复握手
        - refresh_token 变化将触发旧客户端清理，随后创建新实例
        - 通过 `_clients_lock` 确保在并发场景下的状态一致性

        Args:
            email: 账户邮箱地址（大小写敏感处理前）
            account_info: 账户凭证，至少包含 refresh_token

        Returns:
            对应邮箱的 IMAPEmailClient 实例
        """
        async with self._get_clients_lock():
            refresh_token = account_info.get("refresh_token", "")
            client = self._clients.get(email)

            if client and self._client_tokens.get(email) == refresh_token:
                self._metrics["client_reuses"] += 1
                return client

            if client:
                try:
                    await client.cleanup()
                except Exception as exc:
                    logger.warning(f"释放IMAP客户端失败({email}): {exc}")

            new_client = IMAPEmailClient(email, account_info)
            self._clients[email] = new_client
            self._client_tokens[email] = refresh_token
            self._metrics["client_creates"] += 1
            return new_client

    async def get_messages(
        self, email: str, top: Optional[int] = None, folder: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        if not email or not email.strip():
            raise HTTPException(status_code=400, detail=ERROR_EMAIL_NOT_PROVIDED)

        actual_email, account_info = await self._get_account_info(email)
        client = await self._get_or_create_client(actual_email, account_info)
        limit = self._normalize_limit(top)

        folder_id = folder or INBOX_FOLDER_NAME
        logger.info(f"开始获取 {actual_email} ({folder_id}) 的最新 {limit} 封邮件")
        return await client.get_messages_with_content(folder_id=folder_id, top=limit)

    async def cleanup_all(self) -> None:
        async with self._get_clients_lock():
            clients = list(self._clients.values())
            self._clients.clear()
            self._client_tokens.clear()

        for client in clients:
            try:
                await client.cleanup()
            except Exception as exc:
                logger.warning(f"清理IMAP客户端失败: {exc}")

    async def get_metrics(self) -> Dict[str, Any]:
        """返回当前性能指标快照并落盘"""
        hits = self._metrics.get("cache_hits", 0)
        misses = self._metrics.get("cache_misses", 0)
        total = hits + misses
        hit_rate = round(hits / total, 3) if total else None

        snapshot = {
            **self._metrics,
            "accounts_source": self._accounts_source,
            "accounts_count": len(self._accounts_cache or {}),
            "cache_hit_rate": hit_rate,
        }

        cache_stats = await db_manager.get_email_cache_stats()
        snapshot["email_cache"] = cache_stats

        await db_manager.upsert_system_metric("email_manager", snapshot)
        return snapshot


    @staticmethod
    def _normalize_limit(top: Optional[int]) -> int:
        if top is None:
            value = DEFAULT_EMAIL_LIMIT
        else:
            try:
                value = int(top)
            except (TypeError, ValueError):
                value = DEFAULT_EMAIL_LIMIT

        return max(MIN_EMAIL_LIMIT, min(MAX_EMAIL_LIMIT, value))


email_manager = EmailManager()


async def load_accounts_config(force_refresh: bool = False) -> Dict[str, Dict[str, str]]:
    """提供给路由的账户加载入口"""
    return await email_manager.load_accounts(force_refresh=force_refresh)


# ============================================================================
# 账户合并辅助函数 (重构后提取的独立函数)
# ============================================================================


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
    """准备并验证账户数据

    Args:
        accounts: 待导入的账户列表

    Returns:
        (prepared, error_details, error_count)
        - prepared: 规范化后的账户字典 {normalized_email: {email, password, client_id, refresh_token}}
        - error_details: 错误详情列表
        - error_count: 错误数量
    """
    prepared: Dict[str, Dict[str, str]] = {}
    error_details: List[Dict[str, str]] = []
    error_count = 0

    for idx, account in enumerate(accounts, 1):
        original_email = (account.email or "").strip()
        normalized_email = _normalize_email(original_email)
        refresh_token = (account.refresh_token or "").strip()

        # 验证必填字段
        if not normalized_email:
            error_count += 1
            error_details.append({
                "action": "error",
                "email": original_email,
                "message": f"第{idx}条缺少有效邮箱"
            })
            continue

        if not refresh_token:
            error_count += 1
            error_details.append({
                "action": "error",
                "email": original_email or normalized_email,
                "message": f"{original_email or normalized_email} 缺少 refresh_token"
            })
            continue

        # 准备账户数据(加密敏感信息)
        entry_email = original_email or normalized_email
        password_plain = (account.password or "").strip()
        prepared[normalized_email] = {
            "email": original_email or normalized_email,
            "password": encrypt_if_needed(password_plain) if password_plain else "",
            "client_id": (account.client_id or CLIENT_ID).strip() or CLIENT_ID,
            "refresh_token": encrypt_if_needed(refresh_token),
        }

        # 验证账户信息
        validation_errors = _validate_account_info(entry_email, prepared[normalized_email])
        if validation_errors:
            error_count += 1
            error_details.append({
                "action": "error",
                "email": entry_email,
                "message": "; ".join(validation_errors)
            })
            prepared.pop(normalized_email, None)
            continue

    return prepared, error_details, error_count


async def _handle_replace_mode(
    prepared: Dict[str, Dict[str, str]],
    total_count: int,
    error_count: int,
    error_details: List[Dict[str, str]]
) -> ImportResult:
    """处理replace模式的账户导入

    Args:
        prepared: 已准备好的账户字典
        total_count: 总账户数
        error_count: 错误数量
        error_details: 错误详情列表

    Returns:
        ImportResult对象
    """
    # 构建valid_accounts字典
    valid_accounts = {
        info["email"]: {
            "password": info["password"],
            "client_id": info["client_id"],
            "refresh_token": info["refresh_token"],
        }
        for info in prepared.values()
    }

    # 检查是否有有效账户
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

    # 执行替换操作
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

    # 替换失败
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
    merge_mode: str
) -> Tuple[str, Dict[str, str]]:
    """处理单个账户的update/skip/add逻辑

    Args:
        normalized_email: 规范化后的邮箱
        info: 账户信息字典
        lookup_existing: 现有账户查找字典
        merge_mode: 合并模式

    Returns:
        (action, detail) - 操作类型和详情
    """
    email_to_use = lookup_existing.get(normalized_email, info["email"] or normalized_email)
    payload = {
        "password": info["password"],
        "client_id": info["client_id"],
        "refresh_token": info["refresh_token"],
    }

    # 账户已存在
    if normalized_email in lookup_existing:
        # skip模式:跳过已存在的账户
        if merge_mode == "skip":
            return "skipped", {
                "action": "skipped",
                "email": info["email"],
                "message": "已存在，按照 skip 策略跳过"
            }

        # update模式:更新已存在的账户
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
                "message": "账户已更新"
            }
        else:
            return "error", {
                "action": "error",
                "email": lookup_existing[normalized_email],
                "message": "更新账户失败"
            }

    # 账户不存在:添加新账户
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
            "message": "账户已添加"
        }
    else:
        return "error", {
            "action": "error",
            "email": email_to_use,
            "message": "添加账户失败"
        }


async def _handle_update_skip_mode(
    prepared: Dict[str, Dict[str, str]],
    merge_mode: str
) -> ImportStats:
    """处理update/skip模式的账户导入"""
    stats = ImportStats()

    # 获取现有账户
    existing_accounts = await db_manager.get_all_accounts()
    lookup_existing = {addr.lower(): addr for addr in existing_accounts.keys()}

    # 遍历prepared账户
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
    details: List[Dict[str, str]]
) -> ImportResult:
    """构建导入结果对象

    Args:
        total_count: 总账户数
        added_count: 新增数量
        updated_count: 更新数量
        skipped_count: 跳过数量
        error_count: 错误数量
        details: 详情列表

    Returns:
        ImportResult对象
    """
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
    merge_mode: str = "update"
) -> ImportResult:
    """根据不同模式合并账户数据(重构后版本)

    重构改进:
    - 将194行大函数拆分为5个职责单一的辅助函数
    - 主函数简化为~40行,逻辑清晰易读
    - 提高代码可测试性和可维护性

    Args:
        accounts: 待导入的账户列表
        merge_mode: 合并模式 (replace/update/skip)

    Returns:
        ImportResult对象
    """
    # 1. 验证模式
    merge_mode = (merge_mode or "update").lower()
    if merge_mode not in VALID_MERGE_MODES:
        merge_mode = "update"

    total_count = len(accounts)

    # 2. 准备并验证账户数据
    prepared, error_details, error_count = _prepare_and_validate_accounts(accounts)

    # 3. 根据模式处理
    if merge_mode == "replace":
        return await _handle_replace_mode(prepared, total_count, error_count, error_details)

    # 4. 处理update/skip模式
    stats = await _handle_update_skip_mode(prepared, merge_mode)
    error_count += stats.errors
    all_details = error_details + stats.details

    # 5. 使缓存失效
    if stats.added or stats.updated:
        await email_manager.invalidate_accounts_cache()

    # 6. 构建并返回结果
    return _build_import_result(
        total_count, stats.added, stats.updated, stats.skipped, error_count, all_details
    )


async def load_system_config() -> Dict[str, Any]:
    """加载系统配置（DB 优先，文件作为后备）"""
    config = dict(SYSTEM_CONFIG_DEFAULTS)
    config.update(_read_system_config_file())

    for key in SYSTEM_CONFIG_DEFAULTS.keys():
        db_value = await db_manager.get_system_config(key)
        if db_value is not None:
            config[key] = _cast_system_value(key, db_value)
        else:
            config[key] = _cast_system_value(key, config.get(key))

    return config


async def set_system_config_value(key: str, value: Any) -> bool:
    """更新配置值并持久化到数据库与文件"""
    config = await load_system_config()
    config[key] = _cast_system_value(key, value)

    await _write_system_config_file(config)
    success = await db_manager.set_system_config(key, str(config[key]))
    return success


async def get_system_config_value(key: str, default: Optional[Any] = None) -> Any:
    config = await load_system_config()
    return config.get(key, default)


__all__ = [
    "email_manager",
    "load_accounts_config",
    "merge_accounts_data_to_db",
    "load_system_config",
    "set_system_config_value",
    "get_system_config_value",
    "db_manager",
    "parse_account_line",
]
