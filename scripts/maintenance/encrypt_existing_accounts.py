#!/usr/bin/env python3
"""
数据库迁移脚本 - 加密现有账户的敏感信息

此脚本将数据库中所有账户的明文密码和 refresh_token 加密存储

使用方法:
1. 备份数据库文件: cp data/outlook_manager.db data/outlook_manager.db.backup
2. 配置环境变量 DATA_ENCRYPTION_KEY
3. 运行脚本: python scripts/encrypt_existing_accounts.py
4. 验证加密后的数据可以正常使用

注意:
- 运行前务必备份数据库
- 确保 DATA_ENCRYPTION_KEY 已配置且不会丢失
- 脚本会跳过已加密的数据,可以安全地重复运行
"""

import sys
import os
import asyncio
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "backend"))

from app.database import db_manager
from app.security import encrypt_if_needed, is_encrypted

async def migrate_accounts():
    """迁移所有账户的敏感信息"""
    print("=" * 60)
    print("开始加密数据库中的敏感信息")
    print("=" * 60)
    
    try:
        # 获取所有账户
        accounts = await db_manager.get_all_accounts()
        total = len(accounts)
        print(f"\n找到 {total} 个账户")
        
        if total == 0:
            print("数据库中没有账户,无需迁移")
            return
        
        # 统计信息
        encrypted_count = 0
        skipped_count = 0
        error_count = 0
        
        # 逐个处理账户
        for i, account in enumerate(accounts, 1):
            email = account.get("email", "未知")
            print(f"\n[{i}/{total}] 处理账户: {email}")
            
            try:
                # 检查并加密密码
                password = account.get("password", "")
                if password:
                    if is_encrypted(password):
                        print(f"  - 密码已加密,跳过")
                        skipped_count += 1
                    else:
                        encrypted_password = encrypt_if_needed(password)
                        account["password"] = encrypted_password
                        print(f"  - 密码已加密")
                        encrypted_count += 1
                else:
                    print(f"  - 无密码")
                
                # 检查并加密 refresh_token
                refresh_token = account.get("refresh_token", "")
                if refresh_token:
                    if is_encrypted(refresh_token):
                        print(f"  - Refresh token 已加密,跳过")
                        if password and not is_encrypted(password):
                            skipped_count += 1
                    else:
                        encrypted_token = encrypt_if_needed(refresh_token)
                        account["refresh_token"] = encrypted_token
                        print(f"  - Refresh token 已加密")
                        encrypted_count += 1
                else:
                    print(f"  - 无 refresh token")
                
                # 更新数据库
                await db_manager.update_account(email, account)
                print(f"  ✓ 账户更新成功")
                
            except Exception as e:
                print(f"  ✗ 处理失败: {e}")
                error_count += 1
                continue
        
        # 输出统计信息
        print("\n" + "=" * 60)
        print("迁移完成")
        print("=" * 60)
        print(f"总账户数: {total}")
        print(f"新加密字段数: {encrypted_count}")
        print(f"已加密跳过数: {skipped_count}")
        print(f"错误数: {error_count}")
        
        if error_count > 0:
            print("\n⚠️  部分账户处理失败,请检查日志")
            sys.exit(1)
        else:
            print("\n✓ 所有账户处理成功")
            
    except Exception as e:
        print(f"\n✗ 迁移失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        # 关闭数据库连接
        db_manager.close()


def check_environment():
    """检查环境配置"""
    print("检查环境配置...")
    
    # 检查 DATA_ENCRYPTION_KEY
    if not os.getenv("DATA_ENCRYPTION_KEY"):
        print("✗ 错误: DATA_ENCRYPTION_KEY 未配置")
        print("\n请设置环境变量:")
        print('  export DATA_ENCRYPTION_KEY="your-secret-key"')
        print("\n或创建 .env 文件并添加:")
        print('  DATA_ENCRYPTION_KEY=your-secret-key')
        sys.exit(1)
    
    print("✓ DATA_ENCRYPTION_KEY 已配置")
    
    # 检查数据库文件
    db_path = project_root / "data" / "outlook_manager.db"
    if not db_path.exists():
        print(f"✗ 错误: 数据库文件不存在: {db_path}")
        sys.exit(1)
    
    print(f"✓ 数据库文件存在: {db_path}")
    
    # 检查备份
    backup_path = db_path.with_suffix(".db.backup")
    if not backup_path.exists():
        print(f"\n⚠️  警告: 未找到备份文件: {backup_path}")
        response = input("是否继续? (yes/no): ")
        if response.lower() != "yes":
            print("已取消")
            sys.exit(0)
    else:
        print(f"✓ 找到备份文件: {backup_path}")


if __name__ == "__main__":
    print("数据库敏感信息加密迁移工具")
    print()
    
    # 检查环境
    check_environment()
    
    print("\n准备开始迁移...")
    response = input("确认继续? (yes/no): ")
    if response.lower() != "yes":
        print("已取消")
        sys.exit(0)
    
    # 执行迁移
    asyncio.run(migrate_accounts())
