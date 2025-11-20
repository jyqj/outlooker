#!/usr/bin/env python3
"""
阶段一安全改进测试脚本

此脚本自动验证 S1-S6 的所有安全改进是否正常工作

使用方法:
    python scripts/test_security_improvements.py

测试项目:
    [S1] JWT 密钥安全性
    [S2] 管理员账号密码安全性
    [S3] Legacy Token 收敛
    [S4] CORS 配置
    [S5] 敏感日志清理
    [S6] 敏感信息加密存储
"""

import os
import sys
import asyncio
from pathlib import Path
from typing import Dict, List, Tuple

# 添加项目路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "backend"))

# 颜色输出
class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    RESET = '\033[0m'
    BOLD = '\033[1m'

def print_header(text: str):
    print(f"\n{Colors.BOLD}{Colors.BLUE}{'='*60}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.BLUE}{text}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.BLUE}{'='*60}{Colors.RESET}\n")

def print_test(name: str):
    print(f"{Colors.BOLD}测试: {name}{Colors.RESET}")

def print_success(message: str):
    print(f"  {Colors.GREEN}✓ {message}{Colors.RESET}")

def print_error(message: str):
    print(f"  {Colors.RED}✗ {message}{Colors.RESET}")

def print_warning(message: str):
    print(f"  {Colors.YELLOW}⚠ {message}{Colors.RESET}")

def print_info(message: str):
    print(f"  {Colors.BLUE}ℹ {message}{Colors.RESET}")

# 测试结果统计
test_results: List[Tuple[str, bool, str]] = []

def add_result(test_name: str, passed: bool, message: str = ""):
    test_results.append((test_name, passed, message))

async def test_s1_jwt_secret():
    """测试 S1: JWT 密钥安全性"""
    print_header("[S1] JWT 密钥安全性测试")
    
    # 测试 1: 检查 JWT_SECRET_KEY 是否配置
    print_test("检查 JWT_SECRET_KEY 环境变量")
    jwt_secret = os.getenv("JWT_SECRET_KEY")
    if jwt_secret:
        print_success(f"JWT_SECRET_KEY 已配置 (长度: {len(jwt_secret)})")
        add_result("S1-1: JWT_SECRET_KEY 配置", True)
    else:
        print_error("JWT_SECRET_KEY 未配置")
        add_result("S1-1: JWT_SECRET_KEY 配置", False, "未设置环境变量")
    
    # 测试 2: 验证 jwt_auth.py 中的强制检查
    print_test("验证 jwt_auth.py 强制检查逻辑")
    try:
        # 临时移除环境变量测试
        original_key = os.environ.get("JWT_SECRET_KEY")
        if original_key:
            del os.environ["JWT_SECRET_KEY"]
        
        # 重新导入应该抛出异常
        import importlib
        import jwt_auth
        importlib.reload(jwt_auth)
        
        print_error("未抛出 RuntimeError,检查失败")
        add_result("S1-2: JWT 强制检查", False, "应该抛出 RuntimeError")
        
        # 恢复环境变量
        if original_key:
            os.environ["JWT_SECRET_KEY"] = original_key
            
    except RuntimeError as e:
        if "JWT_SECRET_KEY" in str(e):
            print_success(f"正确抛出 RuntimeError: {e}")
            add_result("S1-2: JWT 强制检查", True)
        else:
            print_error(f"RuntimeError 消息不正确: {e}")
            add_result("S1-2: JWT 强制检查", False, str(e))
        
        # 恢复环境变量
        if original_key:
            os.environ["JWT_SECRET_KEY"] = original_key
            import importlib
            import jwt_auth
            importlib.reload(jwt_auth)
    except Exception as e:
        print_error(f"意外错误: {e}")
        add_result("S1-2: JWT 强制检查", False, str(e))

async def test_s2_admin_credentials():
    """测试 S2: 管理员账号密码安全性"""
    print_header("[S2] 管理员账号密码安全性测试")
    
    # 测试 1: 检查环境变量
    print_test("检查管理员账号配置")
    app_env = os.getenv("APP_ENV", "development")
    admin_username = os.getenv("ADMIN_USERNAME")
    admin_password = os.getenv("ADMIN_PASSWORD")
    
    print_info(f"当前环境: {app_env}")
    
    if admin_username and admin_password:
        print_success(f"管理员账号已配置: {admin_username}")
        add_result("S2-1: 管理员账号配置", True)
    else:
        if app_env == "production":
            print_error("生产环境必须配置管理员账号")
            add_result("S2-1: 管理员账号配置", False, "生产环境缺少配置")
        else:
            print_warning("开发环境未配置管理员账号,将使用默认值")
            add_result("S2-1: 管理员账号配置", True, "开发环境允许默认值")

async def test_s3_legacy_token():
    """测试 S3: Legacy Token 收敛"""
    print_header("[S3] Legacy Token 收敛测试")

    # 测试 1: 检查 ENABLE_LEGACY_ADMIN_TOKEN 配置
    print_test("检查 ENABLE_LEGACY_ADMIN_TOKEN 配置")
    try:
        from config import ENABLE_LEGACY_ADMIN_TOKEN, LEGACY_ADMIN_TOKEN

        if ENABLE_LEGACY_ADMIN_TOKEN:
            print_warning("Legacy token 已启用")
            if LEGACY_ADMIN_TOKEN == "admin123":
                print_error("使用了不安全的默认 token")
                add_result("S3-1: Legacy token 配置", False, "不安全的默认值")
            else:
                print_success("Legacy token 已配置自定义值")
                add_result("S3-1: Legacy token 配置", True)
        else:
            print_success("Legacy token 已禁用 (推荐)")
            add_result("S3-1: Legacy token 配置", True)
    except Exception as e:
        print_error(f"导入配置失败: {e}")
        add_result("S3-1: Legacy token 配置", False, str(e))
        return

    # 测试 2: 验证 verify_legacy_token 逻辑
    print_test("验证 verify_legacy_token 函数")
    try:
        # 需要临时设置 JWT_SECRET_KEY 才能导入 jwt_auth
        original_key = os.environ.get("JWT_SECRET_KEY")
        if not original_key:
            os.environ["JWT_SECRET_KEY"] = "temp_test_key_for_testing_only"

        from jwt_auth import verify_legacy_token

        if not ENABLE_LEGACY_ADMIN_TOKEN:
            result = verify_legacy_token("any_token")
            if not result:
                print_success("Legacy token 验证已禁用")
                add_result("S3-2: Legacy token 验证", True)
            else:
                print_error("Legacy token 应该被拒绝")
                add_result("S3-2: Legacy token 验证", False)
        else:
            # 测试默认值拒绝
            result = verify_legacy_token("admin123")
            if not result:
                print_success("默认 token 'admin123' 被正确拒绝")
                add_result("S3-2: Legacy token 验证", True)
            else:
                print_error("默认 token 应该被拒绝")
                add_result("S3-2: Legacy token 验证", False)

        # 恢复原始状态
        if not original_key:
            del os.environ["JWT_SECRET_KEY"]

    except Exception as e:
        print_error(f"验证失败: {e}")
        add_result("S3-2: Legacy token 验证", False, str(e))

async def test_s4_cors_config():
    """测试 S4: CORS 配置"""
    print_header("[S4] CORS 配置测试")

    # 测试 1: 检查 ALLOWED_ORIGINS 配置
    print_test("检查 ALLOWED_ORIGINS 配置")
    from config import ALLOWED_ORIGINS

    print_info(f"允许的源: {ALLOWED_ORIGINS}")

    if "*" in ALLOWED_ORIGINS:
        print_error("CORS 配置使用了通配符 '*',不安全")
        add_result("S4-1: CORS 配置", False, "使用了通配符")
    else:
        print_success(f"CORS 已配置白名单: {len(ALLOWED_ORIGINS)} 个域名")
        add_result("S4-1: CORS 配置", True)

    # 测试 2: 验证 mail_api.py 中的配置
    print_test("验证 mail_api.py 使用 ALLOWED_ORIGINS")
    try:
        with open(project_root / "backend" / "app" / "mail_api.py", "r", encoding="utf-8") as f:
            content = f.read()
            if "ALLOWED_ORIGINS" in content and 'allow_origins=ALLOWED_ORIGINS' in content:
                print_success("mail_api.py 正确使用 ALLOWED_ORIGINS")
                add_result("S4-2: mail_api.py 配置", True)
            elif 'allow_origins=["*"]' in content:
                print_error("mail_api.py 仍使用通配符")
                add_result("S4-2: mail_api.py 配置", False, "仍使用通配符")
            else:
                print_warning("无法确认 CORS 配置")
                add_result("S4-2: mail_api.py 配置", True, "需要手动验证")
    except Exception as e:
        print_error(f"读取文件失败: {e}")
        add_result("S4-2: mail_api.py 配置", False, str(e))

async def test_s5_sensitive_logging():
    """测试 S5: 敏感日志清理"""
    print_header("[S5] 敏感日志清理测试")

    # 测试: 检查 routers/accounts.py 是否移除了敏感日志
    print_test("检查 routers/accounts.py 敏感日志")
    try:
        with open(project_root / "backend" / "app" / "routers" / "accounts.py", "r", encoding="utf-8") as f:
            content = f.read()

            # 检查是否包含敏感日志
            sensitive_patterns = [
                "logger.info(f\"完整请求数据:",
                "logger.debug(f\"完整请求数据:",
                "logger.info(request_data)",
            ]

            found_sensitive = False
            for pattern in sensitive_patterns:
                if pattern in content:
                    print_error(f"发现敏感日志: {pattern}")
                    found_sensitive = True

            if not found_sensitive:
                print_success("未发现敏感日志输出")
                add_result("S5-1: 敏感日志清理", True)
            else:
                add_result("S5-1: 敏感日志清理", False, "仍存在敏感日志")

    except Exception as e:
        print_error(f"读取文件失败: {e}")
        add_result("S5-1: 敏感日志清理", False, str(e))

async def test_s6_encryption():
    """测试 S6: 敏感信息加密存储"""
    print_header("[S6] 敏感信息加密存储测试")

    # 测试 1: 检查 DATA_ENCRYPTION_KEY 配置
    print_test("检查 DATA_ENCRYPTION_KEY 环境变量")
    encryption_key = os.getenv("DATA_ENCRYPTION_KEY")
    if encryption_key:
        print_success(f"DATA_ENCRYPTION_KEY 已配置 (长度: {len(encryption_key)})")
        add_result("S6-1: 加密密钥配置", True)
    else:
        print_warning("DATA_ENCRYPTION_KEY 未配置,加密功能将无法使用")
        add_result("S6-1: 加密密钥配置", False, "未设置环境变量")
        return  # 后续测试依赖密钥,直接返回

    # 测试 2: 验证 security.py 模块
    print_test("验证 security.py 模块")
    try:
        from security import encrypt_value, decrypt_value, is_encrypted, encrypt_if_needed, decrypt_if_needed
        print_success("security.py 模块导入成功")
        add_result("S6-2: security.py 模块", True)
    except Exception as e:
        print_error(f"导入失败: {e}")
        add_result("S6-2: security.py 模块", False, str(e))
        return

    # 测试 3: 测试加密/解密功能
    print_test("测试加密/解密功能")
    try:
        test_data = "test_password_123"

        # 加密
        encrypted = encrypt_value(test_data)
        print_info(f"原文: {test_data}")
        print_info(f"密文: {encrypted[:50]}...")

        # 验证密文格式
        if is_encrypted(encrypted):
            print_success("密文格式正确 (以 'gAAAAA' 开头)")
        else:
            print_error("密文格式不正确")
            add_result("S6-3: 加密/解密功能", False, "密文格式错误")
            return

        # 解密
        decrypted = decrypt_value(encrypted)

        if decrypted == test_data:
            print_success("加密/解密功能正常")
            add_result("S6-3: 加密/解密功能", True)
        else:
            print_error(f"解密结果不匹配: {decrypted}")
            add_result("S6-3: 加密/解密功能", False, "解密结果不匹配")

    except Exception as e:
        print_error(f"加密/解密测试失败: {e}")
        add_result("S6-3: 加密/解密功能", False, str(e))

    # 测试 4: 测试 encrypt_if_needed / decrypt_if_needed
    print_test("测试智能加密/解密函数")
    try:
        plain_text = "plain_password"

        # 第一次加密
        encrypted1 = encrypt_if_needed(plain_text)
        # 第二次应该跳过
        encrypted2 = encrypt_if_needed(encrypted1)

        if encrypted1 == encrypted2:
            print_success("encrypt_if_needed 正确跳过已加密数据")
        else:
            print_warning("encrypt_if_needed 可能重复加密")

        # 解密
        decrypted1 = decrypt_if_needed(encrypted1)
        decrypted2 = decrypt_if_needed(plain_text)

        if decrypted1 == plain_text and decrypted2 == plain_text:
            print_success("decrypt_if_needed 正确处理加密和明文数据")
            add_result("S6-4: 智能加密/解密", True)
        else:
            print_error("decrypt_if_needed 处理不正确")
            add_result("S6-4: 智能加密/解密", False)

    except Exception as e:
        print_error(f"智能加密/解密测试失败: {e}")
        add_result("S6-4: 智能加密/解密", False, str(e))

    # 测试 5: 验证 services.py 集成
    print_test("验证 services.py 集成加密逻辑")
    try:
        with open(project_root / "backend" / "app" / "services.py", "r", encoding="utf-8") as f:
            content = f.read()

            checks = [
                ("导入加密函数", "from security import encrypt_if_needed, decrypt_if_needed"),
                ("写入时加密", "encrypt_if_needed("),
                ("读取时解密", "decrypt_if_needed("),
            ]

            all_passed = True
            for check_name, pattern in checks:
                if pattern in content:
                    print_success(f"{check_name}: ✓")
                else:
                    print_error(f"{check_name}: ✗")
                    all_passed = False

            if all_passed:
                add_result("S6-5: services.py 集成", True)
            else:
                add_result("S6-5: services.py 集成", False, "缺少必要的集成")

    except Exception as e:
        print_error(f"验证失败: {e}")
        add_result("S6-5: services.py 集成", False, str(e))

def print_summary():
    """打印测试总结"""
    print_header("测试总结")

    total = len(test_results)
    passed = sum(1 for _, p, _ in test_results if p)
    failed = total - passed

    print(f"总测试数: {total}")
    print(f"{Colors.GREEN}通过: {passed}{Colors.RESET}")
    print(f"{Colors.RED}失败: {failed}{Colors.RESET}")
    print()

    if failed > 0:
        print(f"{Colors.BOLD}失败的测试:{Colors.RESET}")
        for name, passed, message in test_results:
            if not passed:
                print(f"  {Colors.RED}✗ {name}{Colors.RESET}")
                if message:
                    print(f"    原因: {message}")

    print()
    if failed == 0:
        print(f"{Colors.GREEN}{Colors.BOLD}✓ 所有测试通过!{Colors.RESET}")
        return 0
    else:
        print(f"{Colors.RED}{Colors.BOLD}✗ 部分测试失败,请检查配置{Colors.RESET}")
        return 1

async def main():
    """主测试函数"""
    print(f"{Colors.BOLD}{Colors.BLUE}")
    print("=" * 60)
    print("  阶段一安全改进测试脚本")
    print("  Outlook Manager 项目")
    print("=" * 60)
    print(f"{Colors.RESET}")

    # 运行所有测试
    await test_s1_jwt_secret()
    await test_s2_admin_credentials()
    await test_s3_legacy_token()
    await test_s4_cors_config()
    await test_s5_sensitive_logging()
    await test_s6_encryption()

    # 打印总结
    exit_code = print_summary()

    return exit_code

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
