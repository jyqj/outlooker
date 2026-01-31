#!/usr/bin/env python3
"""
OAuth2 认证模块单元测试

测试 auth 模块中的令牌获取和刷新功能
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
import httpx
from fastapi import HTTPException

from app.auth import get_access_token


class TestGetAccessToken:
    """测试 access token 获取函数"""

    @pytest.mark.asyncio
    async def test_get_access_token_success(self):
        """测试成功获取 access token"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "access_token": "test_access_token",
            "refresh_token": "new_refresh_token",
        }
        mock_response.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient") as mock_client:
            mock_instance = AsyncMock()
            mock_instance.post.return_value = mock_response
            mock_instance.__aenter__.return_value = mock_instance
            mock_instance.__aexit__.return_value = None
            mock_client.return_value = mock_instance

            access_token, refresh_token = await get_access_token("test_refresh_token")

            assert access_token == "test_access_token"
            assert refresh_token == "new_refresh_token"

    @pytest.mark.asyncio
    async def test_get_access_token_no_new_refresh(self):
        """测试获取 token 但没有新的 refresh token"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "access_token": "test_access_token",
        }
        mock_response.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient") as mock_client:
            mock_instance = AsyncMock()
            mock_instance.post.return_value = mock_response
            mock_instance.__aenter__.return_value = mock_instance
            mock_instance.__aexit__.return_value = None
            mock_client.return_value = mock_instance

            access_token, refresh_token = await get_access_token("test_refresh_token")

            assert access_token == "test_access_token"
            assert refresh_token is None

    @pytest.mark.asyncio
    async def test_get_access_token_http_error_check_only(self):
        """测试 HTTP 错误时 check_only 模式返回 None"""
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_response.text = "Unauthorized"

        http_error = httpx.HTTPStatusError(
            "Unauthorized",
            request=MagicMock(),
            response=mock_response
        )

        with patch("httpx.AsyncClient") as mock_client:
            mock_instance = AsyncMock()
            mock_instance.post.return_value = mock_response
            mock_response.raise_for_status.side_effect = http_error
            mock_instance.__aenter__.return_value = mock_instance
            mock_instance.__aexit__.return_value = None
            mock_client.return_value = mock_instance

            access_token, refresh_token = await get_access_token(
                "invalid_refresh_token", 
                check_only=True
            )

            assert access_token is None
            assert refresh_token is None

    @pytest.mark.asyncio
    async def test_get_access_token_http_error_raises(self):
        """测试 HTTP 错误时非 check_only 模式抛出异常"""
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_response.text = "Unauthorized"

        http_error = httpx.HTTPStatusError(
            "Unauthorized",
            request=MagicMock(),
            response=mock_response
        )

        with patch("httpx.AsyncClient") as mock_client:
            mock_instance = AsyncMock()
            mock_instance.post.return_value = mock_response
            mock_response.raise_for_status.side_effect = http_error
            mock_instance.__aenter__.return_value = mock_instance
            mock_instance.__aexit__.return_value = None
            mock_client.return_value = mock_instance

            with pytest.raises(HTTPException) as exc_info:
                await get_access_token("invalid_refresh_token", check_only=False)

            assert exc_info.value.status_code == 401

    @pytest.mark.asyncio
    async def test_get_access_token_network_error_check_only(self):
        """测试网络错误时 check_only 模式返回 None"""
        with patch("httpx.AsyncClient") as mock_client:
            mock_instance = AsyncMock()
            mock_instance.post.side_effect = httpx.RequestError("Network error")
            mock_instance.__aenter__.return_value = mock_instance
            mock_instance.__aexit__.return_value = None
            mock_client.return_value = mock_instance

            access_token, refresh_token = await get_access_token(
                "test_refresh_token",
                check_only=True
            )

            assert access_token is None
            assert refresh_token is None

    @pytest.mark.asyncio
    async def test_get_access_token_network_error_raises(self):
        """测试网络错误时非 check_only 模式抛出异常"""
        with patch("httpx.AsyncClient") as mock_client:
            mock_instance = AsyncMock()
            mock_instance.post.side_effect = httpx.RequestError("Network error")
            mock_instance.__aenter__.return_value = mock_instance
            mock_instance.__aexit__.return_value = None
            mock_client.return_value = mock_instance

            with pytest.raises(HTTPException) as exc_info:
                await get_access_token("test_refresh_token", check_only=False)

            assert exc_info.value.status_code == 500

    @pytest.mark.asyncio
    async def test_get_access_token_missing_token_check_only(self):
        """测试响应中缺少 access_token 时 check_only 模式"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "error_description": "Invalid grant"
        }
        mock_response.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient") as mock_client:
            mock_instance = AsyncMock()
            mock_instance.post.return_value = mock_response
            mock_instance.__aenter__.return_value = mock_instance
            mock_instance.__aexit__.return_value = None
            mock_client.return_value = mock_instance

            access_token, refresh_token = await get_access_token(
                "test_refresh_token",
                check_only=True
            )

            assert access_token is None
            assert refresh_token is None

    @pytest.mark.asyncio
    async def test_get_access_token_missing_token_raises(self):
        """测试响应中缺少 access_token 时非 check_only 模式"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "error_description": "Invalid grant"
        }
        mock_response.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient") as mock_client:
            mock_instance = AsyncMock()
            mock_instance.post.return_value = mock_response
            mock_instance.__aenter__.return_value = mock_instance
            mock_instance.__aexit__.return_value = None
            mock_client.return_value = mock_instance

            with pytest.raises(HTTPException) as exc_info:
                await get_access_token("test_refresh_token", check_only=False)

            assert exc_info.value.status_code == 401
