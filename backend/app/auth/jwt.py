#!/usr/bin/env python3
"""
JWT 认证模块
处理管理员登录和 JWT token 生成/验证
"""

import logging
from datetime import UTC, datetime, timedelta

from fastapi import Header, HTTPException
from jose import JWTError, jwt
from passlib.context import CryptContext

from ..settings import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

# ============================================================================
# JWT 配置
# ============================================================================

SECRET_KEY: str = settings.jwt_secret_key or ""
if not SECRET_KEY:
    raise RuntimeError("JWT_SECRET_KEY 未配置")

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = settings.access_token_expire_minutes

# 密码哈希上下文
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# ============================================================================
# 密码处理函数
# ============================================================================


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """验证密码"""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """获取密码哈希"""
    return pwd_context.hash(password)


# ============================================================================
# JWT Token 处理函数
# ============================================================================


def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    """创建 JWT access token

    Args:
        data: 要编码的数据（通常包含 sub: username）
        expires_delta: 过期时间增量，如果为 None 则使用默认值

    Returns:
        JWT token 字符串
    """
    to_encode = data.copy()

    now = datetime.now(UTC)
    if expires_delta:
        expire = now + expires_delta
    else:
        expire = now + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode.update({"exp": expire, "iat": now})

    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def decode_access_token(token: str) -> dict | None:
    """解码并验证 JWT token

    Args:
        token: JWT token 字符串

    Returns:
        解码后的数据，如果验证失败则返回 None
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError as e:
        logger.error(f"JWT 解码失败: {e}")
        return None


# ============================================================================
# 认证函数
# ============================================================================


def authenticate_admin(username: str, password: str) -> bool:
    """验证管理员凭证 - 仅支持哈希密码。

    新代码请使用 admin_auth_service.authenticate。
    
    安全要求：
    - 密码必须使用 bcrypt 哈希存储（以 $2b$ 开头）
    - 不再支持明文密码比对
    """
    env_username = settings.admin_username or "admin"
    env_password = settings.admin_password or ""

    if not env_password:
        logger.warning("管理员密码未配置")
        return False
    if username != env_username:
        return False

    # 强制要求使用 bcrypt 哈希密码
    if not env_password.startswith("$2b$"):
        logger.error("安全配置错误: ADMIN_PASSWORD 必须使用 bcrypt 哈希值，不支持明文密码")
        raise RuntimeError(
            "ADMIN_PASSWORD 必须是 bcrypt 哈希值。"
            "请使用 python -c \"from passlib.hash import bcrypt; print(bcrypt.hash('your_password'))\" 生成哈希值"
        )
    
    return verify_password(password, env_password)


def get_current_admin(authorization: str | None = Header(None)) -> str:
    """从请求头获取并验证当前管理员

    Args:
        authorization: Authorization header 值

    Returns:
        管理员用户名

    Raises:
        HTTPException: 如果认证失败
    """
    if not authorization:
        raise HTTPException(status_code=401, detail="未提供认证令牌")

    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="无效的认证格式")

    token = authorization[7:]  # 移除 "Bearer " 前缀

    payload = decode_access_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="无效或过期的令牌")

    username = payload.get("sub")
    if not username:
        raise HTTPException(status_code=401, detail="令牌中缺少用户信息")

    return username
