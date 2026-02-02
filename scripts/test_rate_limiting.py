#!/usr/bin/env python3
"""
登录频率限制测试脚本

测试防爆破功能是否正常工作
"""

import asyncio
import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "backend"))

from app.core.rate_limiter import rate_limiter, auditor


async def test_basic_rate_limiting():
    """测试基本的频率限制功能"""
    print("\n" + "="*60)
    print("测试 1: 基本频率限制")
    print("="*60)
    
    ip = "192.168.1.100"
    username = "test_user"
    
    # 模拟5次失败登录
    for i in range(5):
        await rate_limiter.record_attempt(ip, username, False)
        await auditor.log_attempt(ip, username, False, f"测试失败 #{i+1}")
        
        is_locked, remaining = await rate_limiter.is_locked_out(ip, username)
        attempt_count = await rate_limiter.get_attempt_count(ip, username)
        
        print(f"尝试 {i+1}: 失败次数={attempt_count}, 是否锁定={is_locked}")
    
    # 第6次应该被锁定
    is_locked, remaining = await rate_limiter.is_locked_out(ip, username)
    print(f"\n第6次尝试前检查: 是否锁定={is_locked}, 剩余锁定时间={remaining}秒")
    
    assert is_locked, "应该被锁定"
    assert remaining > 0, "应该有剩余锁定时间"
    
    print("✓ 测试通过: 5次失败后正确触发锁定")


async def test_successful_login_clears_attempts():
    """测试成功登录会清除失败记录"""
    print("\n" + "="*60)
    print("测试 2: 成功登录清除失败记录")
    print("="*60)
    
    ip = "192.168.1.101"
    username = "test_user2"
    
    # 模拟3次失败
    for i in range(3):
        await rate_limiter.record_attempt(ip, username, False)
        await auditor.log_attempt(ip, username, False, f"测试失败 #{i+1}")
    
    attempt_count = await rate_limiter.get_attempt_count(ip, username)
    print(f"失败3次后: 失败次数={attempt_count}")
    assert attempt_count == 3, "应该有3次失败记录"
    
    # 成功登录
    await rate_limiter.record_attempt(ip, username, True)
    await auditor.log_attempt(ip, username, True)
    
    attempt_count = await rate_limiter.get_attempt_count(ip, username)
    is_locked, _ = await rate_limiter.is_locked_out(ip, username)
    
    print(f"成功登录后: 失败次数={attempt_count}, 是否锁定={is_locked}")
    
    assert attempt_count == 0, "成功登录应该清除失败记录"
    assert not is_locked, "成功登录应该解除锁定"
    
    print("✓ 测试通过: 成功登录正确清除失败记录")


async def test_different_users_independent():
    """测试不同用户的限制是独立的"""
    print("\n" + "="*60)
    print("测试 3: 不同用户独立限制")
    print("="*60)
    
    ip = "192.168.1.102"
    user1 = "user1"
    user2 = "user2"
    
    # user1 失败5次
    for i in range(5):
        await rate_limiter.record_attempt(ip, user1, False)
    
    # user2 失败2次
    for i in range(2):
        await rate_limiter.record_attempt(ip, user2, False)
    
    is_locked1, _ = await rate_limiter.is_locked_out(ip, user1)
    is_locked2, _ = await rate_limiter.is_locked_out(ip, user2)
    
    count1 = await rate_limiter.get_attempt_count(ip, user1)
    count2 = await rate_limiter.get_attempt_count(ip, user2)
    
    print(f"用户1: 失败次数={count1}, 是否锁定={is_locked1}")
    print(f"用户2: 失败次数={count2}, 是否锁定={is_locked2}")
    
    assert is_locked1, "用户1应该被锁定"
    assert not is_locked2, "用户2不应该被锁定"
    
    print("✓ 测试通过: 不同用户的限制是独立的")


async def test_different_ips_independent():
    """测试不同 IP 的限制是独立的"""
    print("\n" + "="*60)
    print("测试 4: 不同 IP 独立限制")
    print("="*60)
    
    ip1 = "192.168.1.103"
    ip2 = "192.168.1.104"
    username = "same_user"
    
    # IP1 失败5次
    for i in range(5):
        await rate_limiter.record_attempt(ip1, username, False)
    
    # IP2 失败2次
    for i in range(2):
        await rate_limiter.record_attempt(ip2, username, False)
    
    is_locked1, _ = await rate_limiter.is_locked_out(ip1, username)
    is_locked2, _ = await rate_limiter.is_locked_out(ip2, username)
    
    count1 = await rate_limiter.get_attempt_count(ip1, username)
    count2 = await rate_limiter.get_attempt_count(ip2, username)
    
    print(f"IP1: 失败次数={count1}, 是否锁定={is_locked1}")
    print(f"IP2: 失败次数={count2}, 是否锁定={is_locked2}")
    
    assert is_locked1, "IP1应该被锁定"
    assert not is_locked2, "IP2不应该被锁定"
    
    print("✓ 测试通过: 不同 IP 的限制是独立的")


async def test_audit_logging():
    """测试审计日志记录"""
    print("\n" + "="*60)
    print("测试 5: 审计日志记录")
    print("="*60)
    
    ip = "192.168.1.105"
    username = "audit_test_user"
    
    # 记录几次登录尝试
    await auditor.log_attempt(ip, username, False, "密码错误")
    await auditor.log_attempt(ip, username, False, "密码错误")
    await auditor.log_attempt(ip, username, True)
    
    print("✓ 审计日志已记录")
    print(f"  日志文件: data/logs/login_audit.log")
    print(f"  可使用 'python scripts/view_login_audit.py' 查看")


async def main():
    """运行所有测试"""
    print("\n登录频率限制功能测试")
    print("="*60)
    
    try:
        await test_basic_rate_limiting()
        await test_successful_login_clears_attempts()
        await test_different_users_independent()
        await test_different_ips_independent()
        await test_audit_logging()
        
        print("\n" + "="*60)
        print("✓ 所有测试通过!")
        print("="*60 + "\n")
        
    except AssertionError as e:
        print(f"\n✗ 测试失败: {e}\n")
        sys.exit(1)
    except Exception as e:
        print(f"\n✗ 测试异常: {e}\n")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
