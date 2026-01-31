[← 返回文档目录](./README.md)

# Outlooker 安全改进 - 快速测试参考

本文档提供 Outlooker 项目安全功能的快速测试方法和验证清单。

## 🚀 一键测试

```bash
# 1. 配置环境
cp .env.example .env
nano .env  # 设置必需的密钥

# 2. 运行自动化测试
python scripts/test_security_improvements.py

# 3. 如果有现有数据,运行迁移
python scripts/maintenance/encrypt_existing_accounts.py
```

---

## 🔑 生成密钥

```bash
# JWT 密钥
python -c "import secrets; print('JWT_SECRET_KEY=' + secrets.token_urlsafe(32))"

# 加密密钥
python -c "import secrets; print('DATA_ENCRYPTION_KEY=' + secrets.token_urlsafe(32))"

# 管理员密码
python -c "import secrets; print('ADMIN_PASSWORD=' + secrets.token_urlsafe(16))"
```

---

## ✅ 快速验证清单

### [S1] JWT 密钥
```bash
# 验证: 未配置时应用无法启动
grep JWT_SECRET_KEY .env
```

### [S2] 管理员账号
```bash
# 验证: 生产环境必须配置
grep ADMIN_USERNAME .env
grep ADMIN_PASSWORD .env
```

### [S3] Legacy Token
```bash
# 验证: 默认禁用
grep ENABLE_LEGACY_ADMIN_TOKEN .env
# 应该是 false 或不存在
```

### [S4] CORS 配置
```bash
# 验证: 不使用通配符
grep "allow_origins" backend/app/mail_api.py
# 应该是 allow_origins=ALLOWED_ORIGINS
```

### [S5] 敏感日志
```bash
# 验证: 已删除敏感日志
grep "完整请求数据" backend/app/routers/accounts.py
# 应该无输出
```

### [S6] 数据加密
```bash
# 验证: 数据库中的数据已加密
sqlite3 data/outlook_manager.db \
  "SELECT email, substr(password,1,10) FROM accounts LIMIT 1;"
# password 应该以 'gAAAAA' 开头
```

---

## 🧪 功能测试

```bash
# 1. 启动应用
cd backend && python -m app.mail_api web &

# 2. 登录
curl -X POST http://localhost:5001/api/admin/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"your-password"}'

# 3. 获取账户列表
curl http://localhost:5001/api/accounts \
  -H "Authorization: Bearer YOUR_TOKEN"

# 4. 停止应用
pkill -f "python -m app.mail_api"
```

---

## 🔄 数据库迁移

```bash
# 1. 备份
cp data/outlook_manager.db \
   data/outlook_manager.db.backup

# 2. 配置密钥
echo "DATA_ENCRYPTION_KEY=$(python -c 'import secrets; print(secrets.token_urlsafe(32))')" \
  >> .env

# 3. 运行迁移
python scripts/maintenance/encrypt_existing_accounts.py

# 4. 验证
sqlite3 data/outlook_manager.db \
  "SELECT COUNT(*) FROM accounts WHERE password LIKE 'gAAAAA%';"
```

---

## 🧩 类型检查（mypy）

用于增量提升后端类型标注质量（初始仅检查 `backend/app/services`，后续可逐步扩展）。

```bash
# 1) 安装依赖（包含 mypy）
backend/venv/bin/python -m pip install -r backend/requirements.txt

# 2) 运行 mypy（使用仓库根目录 mypy.ini）
backend/venv/bin/python -m mypy --config-file mypy.ini
```

---

## ⚠️ 故障排查

### 应用无法启动
```bash
# 检查环境变量
cat .env | grep -E "JWT_SECRET_KEY|DATA_ENCRYPTION_KEY"
```

### 迁移失败
```bash
# 检查密钥配置
python -c "import os; print('KEY:', 'SET' if os.getenv('DATA_ENCRYPTION_KEY') else 'NOT SET')"

# 恢复备份
cp data/outlook_manager.db.backup \
   data/outlook_manager.db
```

### 解密失败
```bash
# 检查日志（根据实际部署的日志输出位置，例如 stdout 或集中式日志系统）
# 示例：tail -f data/logs/login_audit.log | grep "解密失败"

# 验证密钥一致性
grep DATA_ENCRYPTION_KEY .env
```

---

## 📊 预期结果

### 自动化测试输出
```
============================================================
  阶段一安全改进测试脚本
  Outlooker 项目
============================================================

============================================================
[S1] JWT 密钥安全性测试
============================================================

测试: 检查 JWT_SECRET_KEY 环境变量
  ✓ JWT_SECRET_KEY 已配置 (长度: 43)

...

============================================================
测试总结
============================================================
总测试数: 15
通过: 15
失败: 0

✓ 所有测试通过!
```

### 迁移脚本输出
```
============================================================
开始加密数据库中的敏感信息
============================================================

找到 5 个账户

[1/5] 处理账户: user1@outlook.com
  - 密码已加密
  - Refresh token 已加密
  ✓ 账户更新成功

...

============================================================
迁移完成
============================================================
总账户数: 5
新加密字段数: 10
已加密跳过数: 0
错误数: 0

✓ 所有账户处理成功
```

---

## 📝 必需的环境变量

```bash
# 最小配置
JWT_SECRET_KEY=<随机生成>
DATA_ENCRYPTION_KEY=<随机生成>
ADMIN_USERNAME=admin
ADMIN_PASSWORD=<随机生成>
APP_ENV=development
ALLOWED_ORIGINS=http://localhost:5173
ENABLE_LEGACY_ADMIN_TOKEN=false
```

---

## 🎯 下一步

测试通过后:
1. ✅ 部署到生产环境
2. ✅ 继续阶段二: 架构优化
3. ✅ 更新文档

详细测试步骤请参考: [安全测试指南](./security-testing.md)
