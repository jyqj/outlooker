# Outlooker 安全测试完整指南

本文档提供详细的步骤来验证 **Outlooker** 项目所有安全改进功能（S1-S6），确保系统符合安全标准。

## 📋 测试清单

- [ ] [S1] JWT 密钥安全性
- [ ] [S2] 管理员账号密码安全性
- [ ] [S3] Legacy Token 收敛
- [ ] [S4] CORS 配置收紧
- [ ] [S5] 敏感日志清理
- [ ] [S6] 敏感信息加密存储

---

## 🚀 快速开始

### 方法一: 自动化测试脚本 (推荐)

```bash
# 1. 配置环境变量
cp .env.example .env

# 2. 编辑 .env 文件,设置必需的配置
nano .env

# 3. 运行自动化测试脚本
python scripts/test_security_improvements.py
```

测试脚本会自动验证所有安全改进,并输出详细的测试报告。

### 方法二: 手动测试 (详细验证)

按照下面的详细步骤逐项测试。

---

## 📝 详细测试步骤

### 准备工作

#### 1. 生成安全密钥

```bash
# 生成 JWT_SECRET_KEY (至少 32 字节)
python -c "import secrets; print('JWT_SECRET_KEY=' + secrets.token_urlsafe(32))"

# 生成 DATA_ENCRYPTION_KEY (至少 32 字节)
python -c "import secrets; print('DATA_ENCRYPTION_KEY=' + secrets.token_urlsafe(32))"

# 生成强管理员密码
python -c "import secrets; print('ADMIN_PASSWORD=' + secrets.token_urlsafe(16))"
```

#### 2. 配置 .env 文件

创建或编辑 `.env`:

```bash
# ============================================================================
# 安全配置 (必需)
# ============================================================================

# JWT 密钥 (必需,生产环境必须设置)
JWT_SECRET_KEY=<使用上面生成的密钥>

# 管理员账号 (生产环境必须设置)
ADMIN_USERNAME=admin
ADMIN_PASSWORD=<使用上面生成的密码>

# 数据加密密钥 (必需,用于加密数据库中的敏感信息)
DATA_ENCRYPTION_KEY=<使用上面生成的密钥>

# ============================================================================
# 环境配置
# ============================================================================

# 环境标识 (development 或 production)
APP_ENV=development

# CORS 白名单 (多个域名用逗号分隔)
ALLOWED_ORIGINS=http://localhost:5173,http://localhost:3000

# 是否启用旧版 LEGACY_ADMIN_TOKEN (建议设为 false)
ENABLE_LEGACY_ADMIN_TOKEN=false

# 旧版 LEGACY_ADMIN_TOKEN (仅在 ENABLE_LEGACY_ADMIN_TOKEN=true 时有效)
# LEGACY_ADMIN_TOKEN=your-custom-token-here

# ============================================================================
# 其他配置
# ============================================================================

# Microsoft OAuth2 Client ID
CLIENT_ID=your-client-id-here

# 默认获取邮件数量
DEFAULT_EMAIL_LIMIT=10
```

#### 3. 备份数据库 (重要!)

```bash
# 如果已有数据库,务必先备份
cp data/outlook_manager.db data/outlook_manager.db.backup
```

---

### [S1] JWT 密钥安全性测试

#### 测试目标
- 验证 JWT_SECRET_KEY 必须配置
- 验证未配置时应用无法启动

#### 测试步骤

**测试 1: 验证配置检查**

```bash
# 1. 临时移除 JWT_SECRET_KEY
cd backend
mv .env .env.backup

# 2. 尝试启动应用 (应该失败)
python -m app.mail_api web

# 预期结果: 抛出 RuntimeError: "JWT_SECRET_KEY 未配置..."
```

**测试 2: 验证正常启动**

```bash
# 1. 恢复配置
mv .env.backup .env

# 2. 启动应用 (应该成功)
python -m app.mail_api web

# 预期结果: 应用正常启动,监听 5001 端口
```

#### 验证标准
- ✅ 未配置 JWT_SECRET_KEY 时抛出 RuntimeError
- ✅ 配置后应用正常启动
- ✅ 错误消息清晰,提示如何配置

---

### [S2] 管理员账号密码安全性测试

#### 测试目标
- 验证生产环境强制配置管理员账号
- 验证开发环境允许默认值

#### 测试步骤

**测试 1: 开发环境 (允许默认值)**

```bash
# 1. 设置为开发环境
echo "APP_ENV=development" > .env.test
cat .env >> .env.test

# 2. 移除管理员配置
sed -i '' '/ADMIN_USERNAME/d' .env.test
sed -i '' '/ADMIN_PASSWORD/d' .env.test

# 3. 使用测试配置启动
cd backend
cp .env .env.backup
cp .env.test .env
python -m app.mail_api web

# 预期结果: 应用正常启动,使用默认账号
```

**测试 2: 生产环境 (强制配置)**

```bash
# 1. 设置为生产环境但不配置管理员账号
echo "APP_ENV=production" > .env.test
cat .env.backup | grep -v ADMIN >> .env.test

# 2. 尝试启动
cp .env.test .env
cd backend
python -m app.mail_api web

# 预期结果: 抛出 RuntimeError: "生产环境必须设置 ADMIN_USERNAME 和 ADMIN_PASSWORD"
```

**测试 3: 恢复配置**

```bash
# 恢复原配置
mv .env.backup .env
rm .env.test
```

#### 验证标准
- ✅ 开发环境允许使用默认账号
- ✅ 生产环境强制配置管理员账号
- ✅ 错误消息清晰

---

### [S3] Legacy Token 收敛测试

#### 测试目标
- 验证 Legacy Token 默认禁用
- 验证拒绝不安全的默认 token

#### 测试步骤

**测试 1: 验证默认禁用**

```bash
# 1. 确保 ENABLE_LEGACY_ADMIN_TOKEN=false (或未设置)
grep ENABLE_LEGACY_ADMIN_TOKEN .env

# 2. 启动应用
cd backend
python -m app.mail_api web &
sleep 3

# 3. 尝试使用 legacy token 访问
curl -X GET http://localhost:5001/api/accounts \
  -H "Authorization: Bearer legacy-token"

# 预期结果: 401 Unauthorized

# 4. 停止应用
pkill -f mail_api.py
```

**测试 2: 验证拒绝默认 token**

```bash
# 1. 启用 legacy token 但使用默认值
echo "ENABLE_LEGACY_ADMIN_TOKEN=true" >> .env
echo "LEGACY_ADMIN_TOKEN=admin123" >> .env

# 2. 启动应用
cd backend
python -m app.mail_api web &
sleep 3

# 3. 预期结果: 应用启动失败并输出错误
#    日志包含 "启用了 legacy admin token 但使用了不安全的默认值"

# 4. 清理
pkill -f mail_api.py
sed -i '' '/ENABLE_LEGACY_ADMIN_TOKEN/d' .env
sed -i '' '/LEGACY_ADMIN_TOKEN/d' .env
```

#### 验证标准
- ✅ Legacy token 默认禁用
- ✅ 启用 legacy token 时必须配置非默认的安全值
- ✅ 日志中记录警告信息

---

### [S4] CORS 配置收紧测试

#### 测试目标
- 验证 CORS 不再使用通配符 "*"
- 验证只允许白名单域名访问

#### 测试步骤

**测试 1: 检查配置文件**

```bash
# 检查 config.py
grep "ALLOWED_ORIGINS" backend/app/config.py

# 预期输出: ALLOWED_ORIGINS 来自环境变量 ALLOWED_ORIGINS（例如默认包含 http://localhost:5173）

# 检查 mail_api.py
grep "allow_origins" backend/app/mail_api.py

# 预期输出: allow_origins=ALLOWED_ORIGINS (不应该是 ["*"])
```

**测试 2: 运行时验证**

```bash
# 1. 启动应用
cd backend
python -m app.mail_api web &
sleep 3

# 2. 从非白名单域名访问 (使用 curl 模拟)
curl -X OPTIONS http://localhost:5001/api/accounts \
  -H "Origin: http://evil.com" \
  -H "Access-Control-Request-Method: GET" \
  -v

# 预期结果: 响应头中不包含 Access-Control-Allow-Origin: http://evil.com

# 3. 从白名单域名访问
curl -X OPTIONS http://localhost:5001/api/accounts \
  -H "Origin: http://localhost:5173" \
  -H "Access-Control-Request-Method: GET" \
  -v

# 预期结果: 响应头包含 Access-Control-Allow-Origin: http://localhost:5173

# 4. 停止应用
pkill -f "python -m app.mail_api"
```

#### 验证标准
- ✅ 配置文件使用 ALLOWED_ORIGINS
- ✅ 不使用通配符 "*"
- ✅ 只允许白名单域名跨域访问

---

### [S5] 敏感日志清理测试

#### 测试目标
- 验证导入接口不再记录完整请求数据
- 验证密码和 token 不会出现在日志中

#### 测试步骤

**测试 1: 代码检查**

```bash
# 检查 routers/accounts.py 是否包含敏感日志
grep -n "完整请求数据" backend/app/routers/accounts.py

# 预期结果: 无输出 (已删除)

grep -n "logger.info(request_data)" backend/app/routers/accounts.py

# 预期结果: 无输出
```

**测试 2: 运行时验证**

```bash
# 1. 启动应用并查看日志
cd backend
python -m app.mail_api web 2>&1 | tee app.log &
sleep 3

# 2. 获取 JWT token
TOKEN=$(curl -X POST http://localhost:5001/api/admin/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"your-password"}' \
  | jq -r '.data.access_token')

# 3. 导入测试账户
curl -X POST http://localhost:5001/api/import \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "accounts": [{
      "email": "test@example.com",
      "password": "SECRET_PASSWORD_123",
      "refresh_token": "SECRET_TOKEN_ABC"
    }],
    "merge_mode": "update"
  }'

# 4. 检查日志
grep "SECRET_PASSWORD_123" app.log
grep "SECRET_TOKEN_ABC" app.log

# 预期结果: 无输出 (密码和 token 不应出现在日志中)

# 5. 清理
pkill -f "python -m app.mail_api"
rm app.log
```

#### 验证标准
- ✅ 代码中已删除敏感日志
- ✅ 运行时日志不包含密码和 token
- ✅ 仍保留必要的操作日志 (如账户数量、操作类型)

---

### [S6] 敏感信息加密存储测试

这是最重要的测试,需要仔细验证。

#### 测试目标
- 验证加密/解密功能正常
- 验证数据库中的敏感信息已加密
- 验证应用功能不受影响

#### 前置条件

```bash
# 1. 确保已配置 DATA_ENCRYPTION_KEY
grep DATA_ENCRYPTION_KEY .env

# 2. 备份数据库
cp data/outlook_manager.db data/outlook_manager.db.backup
```

#### 测试步骤

**测试 1: 加密/解密功能单元测试**

```bash
# 创建测试脚本
cat > test_encryption.py << 'EOF'
#!/usr/bin/env python3
import sys
sys.path.insert(0, 'backend')

from security import encrypt_value, decrypt_value, is_encrypted

# 测试数据
test_password = "MySecretPassword123"
test_token = "0.AXEA1234567890abcdef"

print("测试加密功能...")
print(f"原始密码: {test_password}")

# 加密
encrypted_password = encrypt_value(test_password)
print(f"加密后: {encrypted_password[:50]}...")

# 验证格式
if is_encrypted(encrypted_password):
    print("✓ 密文格式正确")
else:
    print("✗ 密文格式错误")
    sys.exit(1)

# 解密
decrypted_password = decrypt_value(encrypted_password)
print(f"解密后: {decrypted_password}")

# 验证
if decrypted_password == test_password:
    print("✓ 加密/解密功能正常")
else:
    print("✗ 解密结果不匹配")
    sys.exit(1)

print("\n所有测试通过!")
EOF

# 运行测试
python test_encryption.py

# 清理
rm test_encryption.py
```

**测试 2: 迁移现有数据库**

```bash
# 1. 检查迁移脚本
ls -l scripts/encrypt_existing_accounts.py

# 2. 运行迁移脚本
python scripts/encrypt_existing_accounts.py

# 脚本会:
# - 检查环境配置
# - 提示确认备份
# - 逐个加密账户
# - 输出统计信息

# 预期输出示例:
# ============================================================
# 开始加密数据库中的敏感信息
# ============================================================
#
# 找到 5 个账户
#
# [1/5] 处理账户: user1@outlook.com
#   - 密码已加密
#   - Refresh token 已加密
#   ✓ 账户更新成功
# ...
# ============================================================
# 迁移完成
# ============================================================
# 总账户数: 5
# 新加密字段数: 10
# 已加密跳过数: 0
# 错误数: 0
#
# ✓ 所有账户处理成功
```

**测试 3: 验证数据库中的数据已加密**

```bash
# 1. 直接查看数据库 (应该看到密文)
sqlite3 data/outlook_manager.db << 'EOF'
.headers on
.mode column
SELECT
    email,
    substr(password, 1, 30) as password_preview,
    substr(refresh_token, 1, 30) as token_preview
FROM accounts
LIMIT 3;
EOF

# 预期输出:
# email                password_preview              token_preview
# -------------------  ----------------------------  ----------------------------
# user1@outlook.com    gAAAAABl1234567890abcdef...   gAAAAABl9876543210fedcba...
# user2@outlook.com    gAAAAABl2345678901bcdefg...   gAAAAABl8765432109edcbaf...

# 注意: 加密后的数据应该以 'gAAAAA' 开头
```

**测试 4: 验证应用功能正常 (解密逻辑)**

```bash
# 1. 启动应用
cd backend
python -m app.mail_api web &
sleep 3

# 2. 登录获取 token
TOKEN=$(curl -s -X POST http://localhost:5001/api/admin/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"your-password"}' \
  | jq -r '.data.access_token')

# 3. 获取账户列表 (验证能正常读取)
curl -s http://localhost:5001/api/accounts \
  -H "Authorization: Bearer $TOKEN" \
  | jq '.data | length'

# 预期结果: 返回账户数量 (如 5)

# 4. 导出账户 (验证解密逻辑)
curl -s http://localhost:5001/api/export \
  -H "Authorization: Bearer $TOKEN" \
  -o exported.txt

# 5. 检查导出文件 (应该是明文)
head -20 exported.txt

# 预期结果: 看到明文的邮箱、密码、refresh_token
# 格式: email----password----refresh_token----client_id

# 6. 清理
pkill -f "python -m app.mail_api"
rm exported.txt
```

**测试 5: 验证新导入的账户自动加密**

```bash
# 1. 启动应用
cd backend
python -m app.mail_api web &
sleep 3

# 2. 获取 token
TOKEN=$(curl -s -X POST http://localhost:5001/api/admin/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"your-password"}' \
  | jq -r '.data.access_token')

# 3. 导入新账户
curl -X POST http://localhost:5001/api/import \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "accounts": [{
      "email": "newuser@outlook.com",
      "password": "NewPassword123",
      "refresh_token": "0.AXEA_new_token_12345"
    }],
    "merge_mode": "update"
  }'

# 4. 检查数据库 (新账户应该已加密)
sqlite3 data/outlook_manager.db << 'EOF'
SELECT
    email,
    substr(password, 1, 30) as password_preview,
    substr(refresh_token, 1, 30) as token_preview
FROM accounts
WHERE email = 'newuser@outlook.com';
EOF

# 预期结果: password 和 refresh_token 都以 'gAAAAA' 开头

# 5. 验证能正常使用 (测试连接)
curl -X POST http://localhost:5001/api/test-email \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "newuser@outlook.com"
  }'

# 预期结果: 返回连接测试结果 (成功或失败取决于 token 是否有效)

# 6. 清理
pkill -f "python -m app.mail_api"
```

**测试 6: 验证迁移脚本的幂等性**

```bash
# 多次运行迁移脚本,应该安全跳过已加密的数据
python scripts/encrypt_existing_accounts.py

# 预期输出:
# ...
# [1/6] 处理账户: user1@outlook.com
#   - 密码已加密,跳过
#   - Refresh token 已加密,跳过
#   ✓ 账户更新成功
# ...
# 新加密字段数: 0
# 已加密跳过数: 12
```

#### 验证标准
- ✅ 加密/解密单元测试通过
- ✅ 迁移脚本成功加密所有账户
- ✅ 数据库中的敏感字段以密文存储 (以 'gAAAAA' 开头)
- ✅ 应用能正常读取和使用账户 (解密逻辑正常)
- ✅ 导出功能返回明文数据
- ✅ 新导入的账户自动加密
- ✅ 迁移脚本可以安全地重复运行

#### 常见问题排查

**问题 1: 迁移后无法登录邮箱**

```bash
# 原因: 可能是解密失败
# 解决: 检查 DATA_ENCRYPTION_KEY 是否正确

# 1. 查看应用日志
tail -f data/logs/app.log

# 2. 查找解密错误
grep "解密失败" data/logs/app.log

# 3. 如果密钥错误,恢复备份
cp data/outlook_manager.db.backup data/outlook_manager.db
```

**问题 2: 迁移脚本报错**

```bash
# 检查环境变量
python -c "import os; print('DATA_ENCRYPTION_KEY:', 'SET' if os.getenv('DATA_ENCRYPTION_KEY') else 'NOT SET')"

# 检查数据库文件权限
ls -l data/outlook_manager.db
```

**问题 3: 部分账户加密失败**

```bash
# 查看迁移脚本输出的错误信息
# 手动检查失败的账户

sqlite3 data/outlook_manager.db << 'EOF'
SELECT email,
       CASE WHEN password LIKE 'gAAAAA%' THEN 'encrypted' ELSE 'plain' END as pwd_status,
       CASE WHEN refresh_token LIKE 'gAAAAA%' THEN 'encrypted' ELSE 'plain' END as token_status
FROM accounts;
EOF
```

---

## 🎯 完整测试流程 (推荐)

按照以下顺序执行完整测试:

```bash
# 1. 准备环境
cd /path/to/outlooker
cp .env.example .env

# 2. 生成并配置密钥
python -c "import secrets; print('JWT_SECRET_KEY=' + secrets.token_urlsafe(32))" >> .env
python -c "import secrets; print('DATA_ENCRYPTION_KEY=' + secrets.token_urlsafe(32))" >> .env
python -c "import secrets; print('ADMIN_PASSWORD=' + secrets.token_urlsafe(16))" >> .env

# 3. 编辑 .env 文件,设置其他必需配置
nano .env

# 4. 备份数据库 (如果存在)
[ -f data/outlook_manager.db ] && \
  cp data/outlook_manager.db data/outlook_manager.db.backup

# 5. 运行自动化测试脚本
python scripts/test_security_improvements.py

# 6. 如果有现有数据,运行迁移脚本
python scripts/encrypt_existing_accounts.py

# 7. 启动应用并手动测试
cd backend
python -m app.mail_api web

# 8. 在另一个终端测试 API
# (参考上面各个测试的具体步骤)
```

---

## ✅ 测试通过标准

所有测试通过后,应该满足以下条件:

### 配置文件
- ✅ `.env` 文件包含所有必需的安全配置
- ✅ 所有密钥都是随机生成的强密钥
- ✅ 生产环境配置了强管理员密码

### 代码检查
- ✅ `jwt_auth.py` 强制检查 JWT_SECRET_KEY
- ✅ `config.py` 包含 ENABLE_LEGACY_ADMIN_TOKEN 和 ALLOWED_ORIGINS
- ✅ `mail_api.py` 使用 ALLOWED_ORIGINS 而非通配符
- ✅ `routers/accounts.py` 不记录敏感请求数据
- ✅ 服务层与 `security.py` 模块协同集成了加密/解密逻辑

### 运行时验证
- ✅ 应用启动时检查必需的环境变量
- ✅ Legacy token 默认禁用
- ✅ CORS 只允许白名单域名
- ✅ 日志中不包含密码和 token
- ✅ 数据库中的敏感信息已加密
- ✅ 应用功能正常,能正常读取和使用账户

### 数据库状态
- ✅ 所有账户的 password 和 refresh_token 字段已加密
- ✅ 加密后的数据以 'gAAAAA' 开头
- ✅ 导出功能返回明文数据
- ✅ 新导入的账户自动加密

---

## 🔄 回滚方案

如果测试失败或出现问题,可以快速回滚:

```bash
# 1. 停止应用
pkill -f "python -m app.mail_api"

# 2. 恢复数据库备份
cp data/outlook_manager.db.backup data/outlook_manager.db

# 3. 恢复配置文件 (如果需要)
git checkout .env

# 4. 重启应用
cd backend
python -m app.mail_api web
```

---

## 📞 获取帮助

如果遇到问题:

1. 查看应用日志: `tail -f data/logs/app.log`
2. 运行自动化测试脚本查看详细错误: `python scripts/test_security_improvements.py`
3. 检查环境变量配置: `cat .env`
4. 验证数据库状态: `sqlite3 data/outlook_manager.db ".schema accounts"`

---

## 🎉 测试完成

完成所有测试后,您可以:

1. ✅ 将改进部署到生产环境
2. ✅ 继续执行阶段二的架构优化
3. ✅ 更新项目文档和 README

**重要提醒**:
- 妥善保管 `DATA_ENCRYPTION_KEY`,丢失后无法解密数据
- 定期备份数据库和配置文件
- 在生产环境使用强密码和随机密钥
- 监控应用日志,确保没有敏感信息泄露
