#!/usr/bin/env python3
"""
数据库迁移脚本

迁移现在由 backend/app/migrations/__init__.py 统一管理。
此脚本提供命令行入口来执行迁移。
"""

import asyncio
import sys
from pathlib import Path

# 添加后端目录到路径
backend_dir = Path(__file__).parent.parent.parent / "backend"
sys.path.insert(0, str(backend_dir))

from app.migrations import apply_migrations


async def main():
    """运行所有待执行的迁移"""
    print("开始执行数据库迁移...")
    try:
        await apply_migrations()
        print("迁移完成！")
    except Exception as e:
        print(f"迁移失败: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
