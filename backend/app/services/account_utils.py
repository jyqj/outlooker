from __future__ import annotations

from typing import Dict, List, Optional, Tuple

from ..config import CLIENT_ID, logger
from ..database import looks_like_guid
from ..utils.pagination import normalize_email
from .constants import ACCOUNTS_CONFIG_FILES


def _normalize_email(email: str) -> str:
    """向后兼容的邮箱规范化函数包装。

    实际逻辑委托给通用工具 `normalize_email`，方便在其他模块中复用。
    """
    return normalize_email(email)


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


# 内部别名, 兼容现有测试与旧代码
_parse_account_line = parse_account_line
