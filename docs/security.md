[← 返回文档目录](./README.md)

# Outlooker 登录安全机制

## 概述

**Outlooker** 实现了完善的登录安全防护体系，包括:
- **频率限制**: 基于 IP + 用户名的登录频率限制（数据持久化到 SQLite）
- **自动锁定**: 失败次数过多自动锁定账户
- **审计日志**: 记录所有登录尝试用于安全分析（统一保存在 `data/logs/login_audit.log`）
- **刷新令牌**: 管理员登录返回 access/refresh token，可选 httpOnly Cookie

## 功能特性

### 1. 频率限制策略

- **统计窗口**: 5分钟内的失败尝试
- **失败阈值**: 最多允许 5 次失败
- **锁定时长**: 触发后锁定 15 分钟
- **独立限制**: 每个 IP + 用户名组合独立计数

### 2. 安全响应

#### 失败登录响应
```json
{
  "detail": "用户名或密码错误,剩余尝试次数: 3"
}
```

#### 锁定响应 (HTTP 429)
```json
{
  "detail": "登录失败次数过多,请在 847 秒后重试"
}
```

### 3. 审计日志

所有登录尝试都会记录到 `data/logs/login_audit.log`:

```json
{
  "ip": "192.168.1.100",
  "username": "admin",
  "success": false,
  "timestamp": 1700000000.123,
  "datetime": "2025-11-20T00:00:00.123456",
  "reason": "用户名或密码错误"
}
```

## 配置参数

在 `backend/app/core/rate_limiter.py` 中可调整:

```python
MAX_LOGIN_ATTEMPTS = 5      # 最大失败次数
LOCKOUT_DURATION = 900      # 锁定时长(秒) - 15分钟
ATTEMPT_WINDOW = 300        # 统计窗口(秒) - 5分钟
```

## 使用工具

### 查看审计日志

```bash
python3 scripts/maintenance/view_login_audit.py
```

输出包括:
- 登录成功率统计
- 最近登录记录
- 失败尝试统计(按 IP、用户名、组合)
- 24小时活动时间线

### 测试频率限制

```bash
python3 scripts/test_rate_limiting.py
```

运行自动化测试验证:
- 基本频率限制
- 成功登录清除失败记录
- 不同用户/IP 独立限制
- 审计日志记录

## API 集成

### 登录端点

```http
POST /api/admin/login
Content-Type: application/json

{
  "username": "admin",
  "password": "your-password"
}
```

**成功响应 (200)**:
```json
{
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "refresh_token": "rtid.secret",
  "token_type": "bearer",
  "expires_in": 86400,
  "refresh_expires_in": 604800,
  "user": {
    "id": 1,
    "username": "admin",
    "role": "admin",
    "is_active": true
  }
}
```

**失败响应 (401)**:
```json
{
  "detail": "用户名或密码错误,剩余尝试次数: 4"
}
```

**锁定响应 (429)**:
```json
{
  "detail": "登录失败次数过多,请在 847 秒后重试"
}
```

### 刷新令牌端点

```http
POST /api/admin/refresh
Content-Type: application/json

{
  "refresh_token": "your-refresh-token" // 若启用 httpOnly，可依赖 Cookie 省略此字段
}
```

**成功响应 (200)** 同登录成功的结构，access/refresh 均会轮换。

## 安全最佳实践

### 1. 监控审计日志

定期检查审计日志,识别可疑活动:

```bash
# 查看最近的失败登录
python3 scripts/maintenance/view_login_audit.py

# 或直接查看日志文件
tail -f data/logs/login_audit.log
```

### 2. 调整限制参数

根据实际情况调整频率限制参数:

- **更严格**: 减少 `MAX_LOGIN_ATTEMPTS` 或增加 `LOCKOUT_DURATION`
- **更宽松**: 增加 `MAX_LOGIN_ATTEMPTS` 或减少 `LOCKOUT_DURATION`

### 3. IP 白名单 (可选扩展)

如需为特定 IP 设置白名单,可在 `backend/app/core/rate_limiter.py` 中添加:

```python
WHITELISTED_IPS = {"127.0.0.1", "192.168.1.1"}

async def is_locked_out(self, ip: str, username: str):
    if ip in WHITELISTED_IPS:
        return False, None
    # ... 原有逻辑
```

### 4. 反向代理配置

如果使用 Nginx 等反向代理,确保正确传递客户端 IP:

```nginx
location /api/ {
    proxy_pass http://localhost:5001;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
}
```

## 故障排查

### 问题: 无法登录,提示锁定

**原因**: 失败次数过多触发锁定

**解决**:
1. 等待 15 分钟后重试
2. 或手动清除锁定状态(重启应用)

### 问题: 审计日志文件过大

**解决**: 定期归档或清理旧日志

```bash
# 归档旧日志
mv data/logs/login_audit.log \
   data/logs/login_audit.$(date +%Y%m%d).log

# 或只保留最近 N 行
tail -n 10000 data/logs/login_audit.log > temp.log
mv temp.log data/logs/login_audit.log
```

### 问题: 获取不到真实 IP

**原因**: 反向代理未正确配置

**检查**:
1. 确认反向代理设置了 `X-Forwarded-For` 或 `X-Real-IP` 头
2. 查看日志中记录的 IP 是否正确

## 技术实现

### 核心模块

- `backend/app/core/rate_limiter.py`: 频率限制和审计核心逻辑
- `backend/app/routers/auth.py`: 登录端点集成
- `scripts/maintenance/view_login_audit.py`: 审计日志查看工具
- `scripts/test_rate_limiting.py`: 自动化测试

### 数据结构

- **内存存储**: 使用 `defaultdict` 存储尝试记录和锁定状态
- **持久化**: 审计日志以 JSON Lines 格式存储到文件
- **线程安全**: 使用 `asyncio.Lock` 保证并发安全

### 性能考虑

- 自动清理过期记录,避免内存泄漏
- 使用滑动窗口算法,时间复杂度 O(n)
- 审计日志异步写入,不阻塞请求处理

