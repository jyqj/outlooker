# 安全机制

## 1. 认证

- 管理端使用 JWT Bearer Token
- 公共接码接口使用 `X-Public-Token`
- 管理员 refresh cookie 支持轮换

## 2. 数据保护

- `accounts.password`、`accounts.refresh_token` 走加密存储
- `oauth_tokens.access_token`、`oauth_tokens.refresh_token` 也走加密存储
- 敏感字段日志默认脱敏

## 3. 登录保护

- 登录失败次数限制
- 锁定窗口
- 审计日志记录

## 4. Outlook 增强能力安全边界

- `/api/outlook/*` 依赖 feature flags
- 协议链路与 Graph 链路都会写 `account_operation_audit`
- 协议链路中的验证码、canary、proofId 不写明文日志

## 5. 任务中心

- 任务控制接口要求 Bearer Token
- SSE 使用 `token` 查询参数，仅用于当前管理端事件流
- Redis 不可用时事件流会降级，不应影响其它接口

