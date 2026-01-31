#!/usr/bin/env python3
"""
OAuth2认证模块
处理Microsoft OAuth2令牌获取和刷新
"""

import logging

import httpx
from fastapi import HTTPException

from ..settings import get_settings

logger = logging.getLogger(__name__)
_settings = get_settings()
CLIENT_ID = _settings.client_id
TOKEN_URL = _settings.token_url

# ============================================================================
# OAuth2令牌获取函数
# ============================================================================

async def get_access_token(refresh_token: str, check_only: bool = False) -> tuple[str | None, str | None]:
    """使用 refresh_token 获取 access_token，同时返回可能旋转的新 refresh_token

    Args:
        refresh_token: 刷新令牌
        check_only: 如果为True，验证失败时返回None而不是抛出异常

    Returns:
        (access_token, new_refresh_token)
        如果 check_only=True 且验证失败则返回 (None, None)
    """
    data = {
        'client_id': CLIENT_ID,
        'grant_type': 'refresh_token',
        'refresh_token': refresh_token,
        'scope': 'https://outlook.office.com/IMAP.AccessAsUser.All offline_access'
    }

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.post(TOKEN_URL, data=data)
            response.raise_for_status()

        try:
            token_data = response.json()
        except Exception as json_err:
            logger.error(f"解析 access_token 响应 JSON 时出错: {json_err}")
            if check_only:
                return None, None
            raise HTTPException(status_code=401, detail="无法解析服务器响应") from json_err

        access_token = token_data.get('access_token')
        new_refresh_token = token_data.get('refresh_token')

        if not access_token:
            error_msg = f"获取 access_token 失败: {token_data.get('error_description', '响应中未找到 access_token')}"
            logger.error(error_msg)
            if check_only:
                return None, None
            raise HTTPException(status_code=401, detail=error_msg)

        if new_refresh_token and new_refresh_token != refresh_token:
            logger.debug("提示: refresh_token 已被服务器更新")

        return access_token, new_refresh_token

    except HTTPException:
        # 重新抛出 HTTPException（包括我们上面抛出的 401）
        raise
    except httpx.HTTPStatusError as http_err:
        logger.error(f"请求 access_token 时发生HTTP错误: {http_err}")
        if http_err.response is not None:
            logger.error(f"服务器响应状态码: {http_err.response.status_code}")
            logger.debug(f"响应详情(仅调试): {http_err.response.text[:200] if http_err.response.text else ''}")

        if check_only:
            return None, None
        raise HTTPException(status_code=401, detail="Refresh token已过期或无效，需要重新获取授权") from http_err

    except httpx.RequestError as e:
        logger.error(f"请求 access_token 时发生网络错误: {e}")
        if check_only:
            return None, None
        raise HTTPException(status_code=500, detail="Token acquisition failed") from e

    except Exception as e:
        logger.error(f"获取 access_token 时发生未知错误: {e}")
        if check_only:
            return None, None
        raise HTTPException(status_code=500, detail="Token acquisition failed") from e
