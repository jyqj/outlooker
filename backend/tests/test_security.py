#!/usr/bin/env python3
"""
安全模块单元测试
测试加密/解密功能
"""

import pytest
from cryptography.fernet import InvalidToken

from app.security import (
    encrypt_value,
    decrypt_value,
    is_encrypted,
    encrypt_if_needed,
    decrypt_if_needed,
)


class TestEncryption:
    """测试加密解密功能"""

    def test_encrypt_decrypt_roundtrip(self):
        """测试加密解密往返"""
        plaintext = "test_password_123"
        
        # 加密
        ciphertext = encrypt_value(plaintext)
        assert ciphertext != plaintext
        assert len(ciphertext) > len(plaintext)
        
        # 解密
        decrypted = decrypt_value(ciphertext)
        assert decrypted == plaintext

    def test_encrypt_empty_string(self):
        """测试加密空字符串"""
        result = encrypt_value("")
        assert result == ""

    def test_decrypt_empty_string(self):
        """测试解密空字符串"""
        result = decrypt_value("")
        assert result == ""

    def test_is_encrypted_detection(self):
        """测试判断字符串是否已加密"""
        plaintext = "plaintext"
        assert is_encrypted(plaintext) is False
        
        ciphertext = encrypt_value(plaintext)
        assert is_encrypted(ciphertext) is True
        
        # 空字符串不是加密文本
        assert is_encrypted("") is False

    def test_encrypt_if_needed_idempotent(self):
        """测试 encrypt_if_needed 的幂等性"""
        plaintext = "test_password"
        
        # 第一次加密
        encrypted_once = encrypt_if_needed(plaintext)
        assert is_encrypted(encrypted_once)
        
        # 再次调用应该返回相同的密文（已经加密则不再加密）
        encrypted_twice = encrypt_if_needed(encrypted_once)
        assert encrypted_twice == encrypted_once

    def test_decrypt_if_needed_idempotent(self):
        """测试 decrypt_if_needed 的幂等性"""
        plaintext = "test_password"
        
        # 未加密的文本应该直接返回
        result = decrypt_if_needed(plaintext)
        assert result == plaintext
        
        # 加密后再解密
        ciphertext = encrypt_value(plaintext)
        decrypted = decrypt_if_needed(ciphertext)
        assert decrypted == plaintext

    def test_decrypt_if_needed_handles_invalid_ciphertext(self):
        """测试解密无效密文时的处理"""
        # 构造一个看起来像加密文本但实际无效的字符串
        fake_ciphertext = "gAAAAAinvalid_cipher_text"
        
        # 应该返回原值而不是抛出异常
        result = decrypt_if_needed(fake_ciphertext)
        assert result == fake_ciphertext

    def test_decrypt_invalid_token_raises_error(self):
        """测试直接调用 decrypt_value 对无效密文会抛出异常"""
        fake_ciphertext = "gAAAAAinvalid_cipher_text"
        
        with pytest.raises(InvalidToken):
            decrypt_value(fake_ciphertext)

    def test_encrypt_unicode_characters(self):
        """测试加密包含 Unicode 字符的文本"""
        unicode_text = "测试密码123!@#"
        
        ciphertext = encrypt_value(unicode_text)
        assert is_encrypted(ciphertext)
        
        decrypted = decrypt_value(ciphertext)
        assert decrypted == unicode_text

    def test_encrypt_long_text(self):
        """测试加密较长的文本"""
        long_text = "a" * 1000
        
        ciphertext = encrypt_value(long_text)
        assert is_encrypted(ciphertext)
        
        decrypted = decrypt_value(ciphertext)
        assert decrypted == long_text


if __name__ == "__main__":
    pytest.main([__file__, "-v"])


