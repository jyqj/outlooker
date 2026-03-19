# 安全测试指南

## 1. 基础检查

启动前确认：

- `JWT_SECRET_KEY`
- `DATA_ENCRYPTION_KEY`
- `PUBLIC_API_TOKEN`
- 管理员账号密码

## 2. 登录安全

验证内容：

- 错误密码会返回失败
- 频率限制生效
- 锁定逻辑生效
- 审计日志可看到登录事件

## 3. 敏感数据

检查：

- `accounts` 中敏感字段已加密
- `oauth_tokens` 中敏感字段已加密
- 日志中无明文 token、验证码、proof/canary

## 4. Outlook 工作台

检查：

- `/api/outlook/accounts*` 只有管理端 Bearer token 可访问
- 协议操作会写审计
- 任务中心 SSE 在 Redis 不可达时不应打爆 API

## 5. 回归命令

```bash
cd backend && pytest
npm --prefix frontend run test
python3 scripts/run_smoke_tests.py
```

