# API 操作指南

本文档关注常见调用路径，而不是穷举字段。

## 1. 管理员登录

```bash
curl -X POST http://localhost:5001/api/admin/login \
  -H 'Content-Type: application/json' \
  -d '{"username":"admin","password":"admin123"}'
```

拿到 `access_token` 后，在后续管理接口中使用：

```bash
Authorization: Bearer <token>
```

## 2. 旧账户池操作

### 分页查看账户

```bash
curl "http://localhost:5001/api/accounts/paged?page=1&page_size=10" \
  -H "Authorization: Bearer <token>"
```

### 随机取号

```bash
curl -X POST http://localhost:5001/api/accounts/pick \
  -H "Authorization: Bearer <token>" \
  -H 'Content-Type: application/json' \
  -d '{"tag":"注册-Apple","exclude_tags":[],"return_credentials":false}'
```

## 3. Outlook 账户工作台

### 获取 Outlook 账户列表

```bash
curl "http://localhost:5001/api/outlook/accounts?limit=20&offset=0" \
  -H "Authorization: Bearer <token>"
```

### 单个刷新 Token

```bash
curl -X POST http://localhost:5001/api/outlook/accounts/user@example.com/refresh-token \
  -H "Authorization: Bearer <token>"
```

### 批量刷新 Token

```bash
curl -X POST http://localhost:5001/api/outlook/accounts/batch-refresh \
  -H "Authorization: Bearer <token>" \
  -H 'Content-Type: application/json' \
  -d '{"emails":[],"limit":20,"offset":0,"concurrency":5}'
```

### 更新 Profile

```bash
curl -X PATCH http://localhost:5001/api/outlook/accounts/user@example.com/profile \
  -H "Authorization: Bearer <token>" \
  -H 'Content-Type: application/json' \
  -d '{"updates":{"displayName":"New Name"}}'
```

## 4. 协议单次操作

### 测试登录

```bash
curl -X POST http://localhost:5001/api/outlook/protocol/test-login \
  -H "Authorization: Bearer <token>" \
  -H 'Content-Type: application/json' \
  -d '{"email":"user@example.com","password":"pass"}'
```

### 列出 proofs

```bash
curl -X POST http://localhost:5001/api/outlook/protocol/list-proofs \
  -H "Authorization: Bearer <token>" \
  -H 'Content-Type: application/json' \
  -d '{"email":"user@example.com","password":"pass"}'
```

### 绑定恢复邮箱

```bash
curl -X POST http://localhost:5001/api/outlook/protocol/bind \
  -H "Authorization: Bearer <token>" \
  -H 'Content-Type: application/json' \
  -d '{
    "email":"user@example.com",
    "password":"pass",
    "recovery_email":"new@example.com",
    "verification_email":"old@example.com",
    "static_code":"123456"
  }'
```

### 替换恢复邮箱

```bash
curl -X POST http://localhost:5001/api/outlook/protocol/replace \
  -H "Authorization: Bearer <token>" \
  -H 'Content-Type: application/json' \
  -d '{
    "email":"user@example.com",
    "password":"pass",
    "old_email":"old@example.com",
    "new_email":"new@example.com",
    "verification_email":"old@example.com",
    "static_code":"123456"
  }'
```

## 5. 渠道与资源池

### 创建渠道

```bash
curl -X POST http://localhost:5001/api/outlook/channels \
  -H "Authorization: Bearer <token>" \
  -H 'Content-Type: application/json' \
  -d '{"code":"apple","name":"Apple 渠道","priority":10}'
```

### 导入辅助邮箱资源

```bash
curl -X POST http://localhost:5001/api/outlook/resources/aux-emails/import \
  -H "Authorization: Bearer <token>" \
  -H 'Content-Type: application/json' \
  -d '{"items":[{"address":"aux1@example.com"},{"address":"aux2@example.com"}]}'
```

## 6. 任务中心

### 查看任务列表

```bash
curl "http://localhost:5001/api/outlook/tasks" \
  -H "Authorization: Bearer <token>"
```

### 取消任务

```bash
curl -X POST http://localhost:5001/api/outlook/tasks/1/cancel \
  -H "Authorization: Bearer <token>"
```

### 重试任务

```bash
curl -X POST http://localhost:5001/api/outlook/tasks/1/retry \
  -H "Authorization: Bearer <token>"
```

## 7. 实时进度

任务中心前端使用：

```text
GET /api/outlook/tasks/events/stream?token=<jwt>
```

返回 `text/event-stream`。

## 8. 运维建议

- 先启用 Graph，再启用 Protocol，再启用 Channels/Resources/Worker
- 运行协议与任务中心前，先确认 Redis 正常
- 批量操作前建议先执行 smoke script

