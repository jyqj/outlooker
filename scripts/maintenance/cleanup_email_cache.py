#!/usr/bin/env python3
"""\
邮箱缓存清理脚本

用于手动或定时清理 email_cache 表中过期的缓存邮件。

使用方法:
    # 默认清理 30 天以前的缓存
    python scripts/cleanup_email_cache.py

    # 自定义天数,例如清理 7 天以前的缓存
    python scripts/cleanup_email_cache.py 7
"""

import sys
import asyncio
from pathlib import Path
from typing import Optional

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "backend"))

from app.database import db_manager  # type: ignore


async def cleanup_cache(days: int = 30) -> None:
    """清理过期的邮箱缓存

    Args:
        days: 保留天数,默认 30 天,会删除早于当前时间 days 天的缓存记录
    """
    print("=" * 60)
    print(f"开始清理邮箱缓存: 删除 {days} 天前的记录")
    print("=" * 60)

    try:
        deleted = await db_manager.cleanup_old_emails(days=days)
        # cleanup_old_emails 当前未返回删除数量,这里仅输出完成提示
        print("\n缓存清理完成")
        if deleted is not None:
            print(f"删除记录数: {deleted}")
    except Exception as e:
        print(f"清理缓存时出错: {e}")
        raise
    finally:
        db_manager.close()


def parse_days_arg(argv: list[str]) -> Optional[int]:
    """解析命令行中的天数参数"""
    if len(argv) < 2:
        return None
    try:
        value = int(argv[1])
        if value <= 0:
            raise ValueError
        return value
    except ValueError:
        print("无效的天数参数,请使用正整数,例如: python scripts/cleanup_email_cache.py 30")
        sys.exit(1)


if __name__ == "__main__":
    days = parse_days_arg(sys.argv) or 30
    print(f"准备清理 {days} 天前的缓存邮件...")
    asyncio.run(cleanup_cache(days))
