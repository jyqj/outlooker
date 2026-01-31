from __future__ import annotations

import hashlib
import logging
import secrets
import uuid
from datetime import UTC, datetime, timedelta

from fastapi import HTTPException, status

from ..auth.jwt import create_access_token, get_password_hash, verify_password
from ..database import db_manager
from ..settings import get_settings

logger = logging.getLogger(__name__)


class AdminAuthService:
    """管理后台认证服务"""

    def __init__(self) -> None:
        self.settings = get_settings()

    # ------------------------------------------------------------------
    # 管理员账户
    # ------------------------------------------------------------------

    async def bootstrap_default_admin(self) -> None:
        """根据环境变量初始化默认管理员"""
        username = self.settings.admin_username
        password = self.settings.admin_password

        if not username or not password:
            logger.warning("未配置 ADMIN_USERNAME/ADMIN_PASSWORD，跳过默认管理员引导")
            return

        existing = await db_manager.get_admin_by_username(username)
        password_hash = get_password_hash(password)

        if existing:
            # 如果密码发生变化则同步更新
            if not verify_password(password, existing["password_hash"]):
                await db_manager.update_admin_password(int(existing["id"]), password_hash)
                logger.info("更新默认管理员密码: %s", username)
            return

        created_id = await db_manager.create_admin_user(username, password_hash)
        if created_id:
            logger.info("已创建默认管理员账号: %s", username)
        else:
            logger.warning("创建默认管理员账号失败，可能已存在同名用户: %s", username)

    async def authenticate(self, username: str, password: str) -> dict:
        """验证管理员凭证"""
        admin = await db_manager.get_admin_by_username(username)
        if not admin:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="用户名或密码错误")
        if not admin.get("is_active"):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="账号已被禁用")
        if not verify_password(password, admin["password_hash"]):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="用户名或密码错误")
        return admin

    # ------------------------------------------------------------------
    # Token 生成/刷新/撤销
    # ------------------------------------------------------------------

    async def issue_token_pair(
        self,
        admin: dict,
        user_agent: str | None,
        ip_address: str | None,
    ) -> dict:
        """生成 access/refresh token 对"""
        now = datetime.now(UTC)
        access_expires = now + timedelta(minutes=self.settings.access_token_expire_minutes)
        refresh_expires = now + timedelta(days=self.settings.refresh_token_expire_days)

        payload = {
            "sub": admin["username"],
            "role": admin.get("role", "admin"),
            "admin_id": admin["id"],
        }
        access_token = create_access_token(payload, expires_delta=access_expires - now)
        refresh_token, refresh_expires_at = await self._create_refresh_token(
            admin_id=admin["id"],
            expires_at=refresh_expires,
            user_agent=user_agent,
            ip_address=ip_address,
        )

        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "expires_in": int((access_expires - now).total_seconds()),
            "refresh_expires_in": int((refresh_expires_at - now).total_seconds()),
        }

    async def rotate_refresh_token(
        self,
        refresh_token: str,
        user_agent: str | None,
        ip_address: str | None,
    ) -> dict:
        """刷新访问令牌"""
        token_id, secret = self._split_refresh_token(refresh_token)
        record = await db_manager.get_admin_refresh_token(token_id)
        if not record:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="刷新令牌无效")
        if record.get("revoked_at"):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="刷新令牌已失效")

        expires_at = record.get("expires_at")
        if expires_at:
            expires_dt = datetime.fromisoformat(expires_at)
            if expires_dt < datetime.now(UTC):
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="刷新令牌已过期")
        else:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="刷新令牌已过期")
        expected_hash = record["token_hash"]
        if expected_hash != self._hash_secret(secret):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="刷新令牌无效")

        admin = await db_manager.get_admin_by_id(int(record["admin_id"]))
        if not admin or not admin.get("is_active"):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="账号不可用")

        await db_manager.revoke_admin_refresh_token(token_id, reason="rotated")
        return await self.issue_token_pair(admin, user_agent, ip_address)

    async def revoke_refresh_token(self, refresh_token: str) -> bool:
        """撤销刷新令牌"""
        token_id, secret = self._split_refresh_token(refresh_token)
        record = await db_manager.get_admin_refresh_token(token_id)
        if not record:
            return False
        if record.get("token_hash") != self._hash_secret(secret):
            return False
        return await db_manager.revoke_admin_refresh_token(token_id, reason="logout")

    # ------------------------------------------------------------------
    # 内部工具
    # ------------------------------------------------------------------

    async def _create_refresh_token(
        self,
        admin_id: int,
        expires_at: datetime,
        user_agent: str | None,
        ip_address: str | None,
    ) -> tuple[str, datetime]:
        token_id = uuid.uuid4().hex
        secret = secrets.token_urlsafe(32)
        token_hash = self._hash_secret(secret)

        await db_manager.insert_admin_refresh_token(
            token_id=token_id,
            admin_id=admin_id,
            token_hash=token_hash,
            expires_at=expires_at,
            user_agent=user_agent,
            ip_address=ip_address,
        )
        return f"{token_id}.{secret}", expires_at

    @staticmethod
    def _hash_secret(secret: str) -> str:
        return hashlib.sha256(secret.encode("utf-8")).hexdigest()

    @staticmethod
    def _split_refresh_token(token: str) -> tuple[str, str]:
        if not token or "." not in token:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="刷新令牌无效")
        token_id, secret = token.split(".", 1)
        if not token_id or not secret:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="刷新令牌无效")
        return token_id, secret


admin_auth_service = AdminAuthService()
