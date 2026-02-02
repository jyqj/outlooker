#!/usr/bin/env python3
"""
安全模块 - 敏感信息加密/解密
使用 Fernet 对称加密保护数据库中的密码和 refresh_token
"""

import base64
import hashlib
import logging

from cryptography.fernet import Fernet, InvalidToken

from ..settings import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()
FERNET_TOKEN_PREFIX = "gAAAAA"

# ============================================================================
# 加密配置
# ============================================================================

def _get_encryption_key() -> bytes:
    """获取加密密钥
    
    从环境变量 DATA_ENCRYPTION_KEY 读取密钥,并转换为 Fernet 所需的格式
    密钥必须是 32 字节的 URL-safe base64 编码字符串
    """
    key_string = settings.data_encryption_key

    # 使用 SHA256 将任意长度的密钥转换为固定 32 字节
    key_hash = hashlib.sha256(key_string.encode()).digest()
    # 转换为 URL-safe base64 编码
    return base64.urlsafe_b64encode(key_hash)


def _get_fernet() -> Fernet:
    """获取 Fernet 加密实例"""
    return Fernet(_get_encryption_key())


# ============================================================================
# 加密/解密函数
# ============================================================================

def encrypt_value(plaintext: str) -> str:
    """加密字符串
    
    Args:
        plaintext: 明文字符串
        
    Returns:
        加密后的字符串 (base64 编码)
        
    Raises:
        RuntimeError: 如果 DATA_ENCRYPTION_KEY 未配置
    """
    if not plaintext:
        return ""

    try:
        fernet = _get_fernet()
        encrypted_bytes = fernet.encrypt(plaintext.encode('utf-8'))
        return encrypted_bytes.decode('utf-8')
    except Exception as e:
        logger.error(f"加密失败: {e}")
        raise


def decrypt_value(ciphertext: str) -> str:
    """解密字符串
    
    Args:
        ciphertext: 加密后的字符串
        
    Returns:
        解密后的明文字符串
        
    Raises:
        RuntimeError: 如果 DATA_ENCRYPTION_KEY 未配置
        InvalidToken: 如果密文无效或密钥错误
    """
    if not ciphertext:
        return ""

    try:
        fernet = _get_fernet()
        decrypted_bytes = fernet.decrypt(ciphertext.encode('utf-8'))
        return decrypted_bytes.decode('utf-8')
    except InvalidToken:
        logger.error("解密失败: 密文无效或密钥错误")
        raise
    except Exception as e:
        logger.error(f"解密失败: {e}")
        raise


# ============================================================================
# 辅助函数
# ============================================================================

def is_encrypted(value: str) -> bool:
    """判断字符串是否已加密
    
    Fernet 加密后的字符串一般以 FERNET_TOKEN_PREFIX 开头 (base64 编码特征)
    
    Args:
        value: 待检查的字符串
        
    Returns:
        True 如果已加密, False 否则
    """
    if not value:
        return False

    # Fernet token 的版本标识 (0x80) 的 base64 形式为 'gAAAAA'
    return value.startswith(FERNET_TOKEN_PREFIX)


def encrypt_if_needed(value: str) -> str:
    """如果未加密则加密
    
    Args:
        value: 待加密的字符串
        
    Returns:
        加密后的字符串 (如果已加密则返回原值)
    """
    if not value:
        return ""

    if is_encrypted(value):
        return value

    return encrypt_value(value)


class DecryptionError(Exception):
    """解密失败异常"""
    pass


def decrypt_if_needed(value: str, raise_on_error: bool = False) -> str:
    """如果已加密则解密
    
    Args:
        value: 待解密的字符串
        raise_on_error: 如果为 True，解密失败时抛出异常；否则返回空字符串
        
    Returns:
        解密后的字符串 (如果未加密则返回原值)
        
    Raises:
        DecryptionError: 当 raise_on_error=True 且解密失败时
    """
    if not value:
        return ""

    if not is_encrypted(value):
        return value

    try:
        return decrypt_value(value)
    except InvalidToken:
        logger.error(
            "解密失败: 密钥可能已更改或数据已损坏。"
            "请检查 DATA_ENCRYPTION_KEY 配置是否正确。"
        )
        if raise_on_error:
            raise DecryptionError("解密失败，密钥可能已更改或数据已损坏")
        # 返回空字符串而非原加密值，防止敏感数据泄露
        return ""


# ============================================================================
# 数据脱敏函数
# ============================================================================

def mask_secret(value: str | None, visible_chars: int = 2, mask_char: str = "*") -> str:
    """
    安全的敏感数据脱敏。
    
    策略：
    - 空值或过短：返回固定掩码
    - 正常值：保留前后各 N 位，中间用掩码替换
    
    Args:
        value: 原始值
        visible_chars: 前后各显示的字符数
        mask_char: 掩码字符
        
    Returns:
        脱敏后的字符串
        
    Examples:
        >>> mask_secret("abcdefghij", 2)
        'ab******ij'
        >>> mask_secret("abc", 2)
        '***'
        >>> mask_secret(None)
        '***'
    """
    if not value:
        return mask_char * 3
        
    length = len(value)
    min_length = visible_chars * 2 + 1
    
    if length <= min_length:
        return mask_char * 3
        
    masked_length = length - visible_chars * 2
    return f"{value[:visible_chars]}{mask_char * masked_length}{value[-visible_chars:]}"


def mask_email(email: str | None) -> str:
    """
    邮箱地址脱敏。
    
    Examples:
        >>> mask_email("user@example.com")
        'us***@example.com'
    """
    if not email or "@" not in email:
        return "***@***"
        
    local, domain = email.rsplit("@", 1)
    masked_local = mask_secret(local, visible_chars=2)
    return f"{masked_local}@{domain}"
