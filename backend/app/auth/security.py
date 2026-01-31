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


def decrypt_if_needed(value: str) -> str:
    """如果已加密则解密
    
    Args:
        value: 待解密的字符串
        
    Returns:
        解密后的字符串 (如果未加密则返回原值)
    """
    if not value:
        return ""

    if not is_encrypted(value):
        return value

    try:
        return decrypt_value(value)
    except InvalidToken:
        logger.warning("解密失败,可能是密钥已更改,返回原值")
        return value
