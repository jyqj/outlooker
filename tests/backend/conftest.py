import sys
from pathlib import Path
import pytest

# 添加 backend 目录到 Python 路径
backend_root = Path(__file__).parent.parent.parent / "backend"
sys.path.insert(0, str(backend_root))


@pytest.fixture
def admin_headers():
    """统一的管理员JWT认证头fixture"""
    from app.auth.jwt import create_access_token
    token = create_access_token({"sub": "admin"})
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def jwt_headers():
    """JWT认证头fixture别名（与admin_headers相同）"""
    from app.auth.jwt import create_access_token
    token = create_access_token({"sub": "admin"})
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(autouse=True)
def reset_public_api_rate_limiter():
    """重置公共接口限流状态，避免用例间互相影响。"""
    from app.core.rate_limiter import public_api_rate_limiter

    # 兼容新旧实现：
    # - 旧版使用 _records (deque)
    # - 新版使用 _PublicApiRateLimiterProxy -> SlidingWindowRateLimiter._windows
    if hasattr(public_api_rate_limiter, "_records"):
        public_api_rate_limiter._records.clear()
    elif hasattr(public_api_rate_limiter, "_limiter") and public_api_rate_limiter._limiter is not None:
        public_api_rate_limiter._limiter._windows.clear()
    # 如果 _limiter 还未初始化，无需清理
