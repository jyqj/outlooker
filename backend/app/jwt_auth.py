#!/usr/bin/env python3
"""
JWT 认证模块
处理管理员登录和 JWT token 生成/验证
"""

from datetime import datetime, timedelta, timezone
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import HTTPException, Header
import logging
import secrets

from .config import LEGACY_ADMIN_TOKEN, ENABLE_LEGACY_ADMIN_TOKEN
from .settings import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

# ============================================================================
# JWT 配置
# ============================================================================

APP_ENV = settings.app_env
SECRET_KEY = settings.jwt_secret_key
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = settings.access_token_expire_minutes

# 密码哈希上下文
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# 默认管理员用户名和密码, 生产环境必须显式配置, 非生产环境允许回退到安全默认值
DEFAULT_ADMIN_USERNAME = settings.admin_username
DEFAULT_ADMIN_PASSWORD = settings.admin_password
if APP_ENV == "production":
    if not DEFAULT_ADMIN_USERNAME or not DEFAULT_ADMIN_PASSWORD:
        raise RuntimeError("生产环境必须设置 ADMIN_USERNAME 和 ADMIN_PASSWORD")
else:
    if not DEFAULT_ADMIN_USERNAME:
        DEFAULT_ADMIN_USERNAME = "admin"
        logger.warning("未设置 ADMIN_USERNAME，开发环境回退为 'admin'")
    if not DEFAULT_ADMIN_PASSWORD:
        # 随机生成一次性密码，防止代码库中存在固定弱口令
        DEFAULT_ADMIN_PASSWORD = secrets.token_urlsafe(24)
        logger.warning(
            "未设置 ADMIN_PASSWORD，开发环境随机生成一次性密码：%s",
            DEFAULT_ADMIN_PASSWORD,
        )

# Legacy token 仅允许在显式配置安全值时启用
if ENABLE_LEGACY_ADMIN_TOKEN:
    if not LEGACY_ADMIN_TOKEN:
        raise RuntimeError("启用了 legacy admin token 但未配置 LEGACY_ADMIN_TOKEN")
    if LEGACY_ADMIN_TOKEN == "admin123":
        raise RuntimeError("启用了 legacy admin token 但使用了不安全的默认值")

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

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """创建 JWT access token
    
    Args:
        data: 要编码的数据（通常包含 sub: username）
        expires_delta: 过期时间增量，如果为 None 则使用默认值
        
    Returns:
        JWT token 字符串
    """
    to_encode = data.copy()
    
    now = datetime.now(timezone.utc)
    if expires_delta:
        expire = now + expires_delta
    else:
        expire = now + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({
        "exp": expire,
        "iat": now
    })
    
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def decode_access_token(token: str) -> Optional[dict]:
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
    """验证管理员用户名和密码
    
    Args:
        username: 用户名
        password: 密码
        
    Returns:
        验证成功返回 True，否则返回 False
    """
    # 简单实现：只验证默认管理员账户
    # 生产环境应该从数据库读取用户信息
    if username != DEFAULT_ADMIN_USERNAME:
        return False
    
    # 检查密码是否为哈希值（以 $2b$ 开头）
    if DEFAULT_ADMIN_PASSWORD.startswith('$2b$'):
        # 已经是哈希值，直接验证
        return verify_password(password, DEFAULT_ADMIN_PASSWORD)
    else:
        # 明文密码，直接比较（向后兼容）
        return password == DEFAULT_ADMIN_PASSWORD

def get_current_admin(authorization: Optional[str] = Header(None)) -> str:
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

# ============================================================================
# 向后兼容函数（用于旧的 ADMIN_TOKEN 方式）
# ============================================================================

def verify_legacy_token(token: str) -> bool:
    """验证旧的固定 token（向后兼容）

    安全策略:
    1. 如果 ENABLE_LEGACY_ADMIN_TOKEN 为 false, 直接拒绝
    2. 如果 LEGACY_ADMIN_TOKEN 仍为默认值 'admin123', 拒绝验证
    3. 只有在显式启用且配置了安全 token 时才允许
    """
    if not ENABLE_LEGACY_ADMIN_TOKEN:
        return False
    if LEGACY_ADMIN_TOKEN == "admin123":
        logger.warning("Legacy token 使用了不安全的默认值, 拒绝验证")
        return False
    if LEGACY_ADMIN_TOKEN:
        return token == LEGACY_ADMIN_TOKEN
    return False
