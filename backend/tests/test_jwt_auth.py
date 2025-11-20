#!/usr/bin/env python3
"""JWT认证模块测试"""

import pytest
from datetime import datetime, timedelta
from jose import jwt, JWTError

from app.jwt_auth import (
    create_access_token,
    decode_access_token,
    authenticate_admin,
    get_current_admin,
    get_password_hash,
    verify_password,
)
from app.settings import get_settings

settings = get_settings()


class TestPasswordHashing:
    """测试密码哈希功能"""

    def test_hash_password_creates_valid_hash(self):
        """测试密码哈希生成"""
        password = "test_password_123"
        hashed = get_password_hash(password)

        assert hashed is not None
        assert hashed != password
        assert hashed.startswith("$2b$")  # bcrypt格式

    def test_verify_password_correct(self):
        """测试正确密码验证"""
        password = "test_password_123"
        hashed = get_password_hash(password)

        assert verify_password(password, hashed) is True

    def test_verify_password_incorrect(self):
        """测试错误密码验证"""
        password = "test_password_123"
        wrong_password = "wrong_password"
        hashed = get_password_hash(password)

        assert verify_password(wrong_password, hashed) is False

    def test_hash_password_different_each_time(self):
        """测试相同密码生成不同哈希(salt随机)"""
        password = "test_password_123"
        hash1 = get_password_hash(password)
        hash2 = get_password_hash(password)

        assert hash1 != hash2
        assert verify_password(password, hash1) is True
        assert verify_password(password, hash2) is True


class TestJWTTokens:
    """测试JWT token功能"""

    def test_create_access_token_default_expiry(self):
        """测试创建token(默认过期时间)"""
        data = {"sub": "test_user"}
        token = create_access_token(data)
        
        assert token is not None
        assert isinstance(token, str)
        
        # 验证token内容
        payload = decode_access_token(token)
        assert payload is not None
        assert payload["sub"] == "test_user"
        assert "exp" in payload

    def test_create_access_token_custom_expiry(self):
        """测试创建token(自定义过期时间)"""
        data = {"sub": "test_user"}
        expires_delta = timedelta(minutes=15)
        token = create_access_token(data, expires_delta)

        payload = decode_access_token(token)
        assert payload is not None
        assert payload["sub"] == "test_user"

    def test_decode_access_token_expired(self):
        """测试过期token验证"""
        data = {"sub": "test_user"}
        # 创建已过期的token
        expires_delta = timedelta(seconds=-1)
        token = create_access_token(data, expires_delta)

        # 验证应该失败
        payload = decode_access_token(token)
        assert payload is None

    def test_decode_access_token_invalid(self):
        """测试无效token验证"""
        invalid_token = "invalid.token.here"
        payload = decode_access_token(invalid_token)
        assert payload is None

    def test_decode_access_token_tampered(self):
        """测试被篡改的token"""
        data = {"sub": "test_user"}
        token = create_access_token(data)

        # 篡改token
        tampered_token = token[:-10] + "tampered12"
        payload = decode_access_token(tampered_token)
        assert payload is None


class TestAdminAuthentication:
    """测试管理员认证功能"""

    def test_authenticate_admin_correct(self):
        """测试正确的管理员凭证"""
        # 注意: 如果密码已经是哈希值,这个测试会失败
        # 在测试环境中,我们使用明文密码
        if settings.admin_password and not settings.admin_password.startswith("$2b$"):
            result = authenticate_admin(
                settings.admin_username,
                settings.admin_password
            )
            assert result is True
        else:
            # 跳过测试,因为密码已经是哈希值
            pytest.skip("Admin password is hashed, cannot test with plain password")

    def test_authenticate_admin_wrong_password(self):
        """测试错误的密码"""
        result = authenticate_admin(
            settings.admin_username,
            "wrong_password"
        )
        assert result is False

    def test_authenticate_admin_wrong_username(self):
        """测试错误的用户名"""
        result = authenticate_admin(
            "wrong_username",
            settings.admin_password
        )
        assert result is False

    def test_get_current_admin_valid_token(self):
        """测试有效token获取管理员信息"""
        # 创建有效token - sub必须是字符串
        username_str = str(settings.admin_username) if settings.admin_username else "admin"
        token = create_access_token({"sub": username_str})
        auth_header = f"Bearer {token}"

        result = get_current_admin(auth_header)
        assert result == username_str

    def test_get_current_admin_invalid_token(self):
        """测试无效token"""
        from fastapi import HTTPException
        
        auth_header = "Bearer invalid_token"
        
        with pytest.raises(HTTPException) as exc_info:
            get_current_admin(auth_header)
        
        assert exc_info.value.status_code == 401

    def test_get_current_admin_missing_bearer(self):
        """测试缺少Bearer前缀"""
        from fastapi import HTTPException
        
        token = create_access_token({"sub": settings.admin_username})
        auth_header = token  # 没有Bearer前缀
        
        with pytest.raises(HTTPException) as exc_info:
            get_current_admin(auth_header)
        
        assert exc_info.value.status_code == 401

