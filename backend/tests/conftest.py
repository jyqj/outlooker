import sys
from pathlib import Path
import pytest

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


@pytest.fixture
def admin_headers():
    """统一的管理员JWT认证头fixture"""
    from app.jwt_auth import create_access_token
    token = create_access_token({"sub": "admin"})
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def jwt_headers():
    """JWT认证头fixture别名（与admin_headers相同）"""
    from app.jwt_auth import create_access_token
    token = create_access_token({"sub": "admin"})
    return {"Authorization": f"Bearer {token}"}

