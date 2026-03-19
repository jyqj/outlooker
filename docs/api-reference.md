# API 参考

本文档只描述当前仓库中已经存在并可运行的接口。

## 1. 认证

### 管理员登录

- `POST /api/admin/login`
- 请求体：

```json
{
  "username": "admin",
  "password": "admin123"
}
```

### 刷新与登出

- `POST /api/admin/refresh`
- `POST /api/admin/logout`

## 2. 公共接码接口

这些接口使用 `X-Public-Token`。

- `GET /api/messages`
- `POST /api/temp-messages`
- `POST /api/test-email`

## 3. 旧后台接口

### 账户

- `GET /api/accounts`
- `GET /api/accounts/paged`
- `POST /api/accounts`
- `GET /api/accounts/{email}`
- `PUT /api/accounts/{email}`
- `DELETE /api/accounts/{email}`
- `POST /api/accounts/pick`
- `POST /api/accounts/health-check`

### 批量

- `POST /api/accounts/batch-delete`
- `POST /api/accounts/batch-tags`
- `POST /api/import`
- `POST /api/parse-import-text`
- `GET /api/export`

### 标签

- `GET /api/accounts/tags`
- `GET /api/accounts/tags/stats`
- `GET /api/accounts/{email}/tags`
- `POST /api/accounts/{email}/tags`
- `GET /api/tags`
- `POST /api/tags`
- `PUT /api/tags/{tag_name}`
- `DELETE /api/tags/{tag_name}`

### 系统

- `GET /api/health`
- `GET /api/health/detailed`
- `GET /api/health/ready`
- `GET /api/health/live`
- `GET /api/system/config`
- `POST /api/system/config`
- `PUT /api/system/config`
- `POST /api/system/cache/refresh`
- `GET /api/system/metrics`
- `GET /api/system/metrics/api`
- `POST /api/system/metrics/reset`
- `GET /api/metrics`
- `GET /api/audit/events`
- `GET /api/system/rules`
- `POST /api/system/rules`
- `DELETE /api/system/rules/{rule_id}`

### 仪表盘

- `GET /api/dashboard/summary`

## 4. Outlook 账户工作台接口

这些接口使用 Bearer JWT。

### 账户与 Token

- `GET /api/outlook/accounts`
- `POST /api/outlook/accounts/batch-refresh`
- `GET /api/outlook/accounts/{email}`
- `POST /api/outlook/accounts/{email}/refresh-token`

### Profile / Settings

- `GET /api/outlook/accounts/{email}/profile`
- `PATCH /api/outlook/accounts/{email}/profile`
- `GET /api/outlook/accounts/{email}/mailbox-settings`
- `PATCH /api/outlook/accounts/{email}/mailbox-settings`
- `GET /api/outlook/accounts/{email}/regional-settings`
- `PATCH /api/outlook/accounts/{email}/regional-settings`

### 安全管理

- `POST /api/outlook/accounts/{email}/change-password`
- `GET /api/outlook/accounts/{email}/auth-methods`
- `GET /api/outlook/accounts/{email}/auth-methods/email`
- `POST /api/outlook/accounts/{email}/auth-methods/email`
- `PUT /api/outlook/accounts/{email}/auth-methods/email/{method_id}`
- `DELETE /api/outlook/accounts/{email}/auth-methods/email/{method_id}`
- `GET /api/outlook/accounts/{email}/auth-methods/totp`
- `DELETE /api/outlook/accounts/{email}/auth-methods/totp/{method_id}`
- `GET /api/outlook/accounts/{email}/auth-methods/phone`
- `POST /api/outlook/accounts/{email}/auth-methods/phone`
- `POST /api/outlook/accounts/{email}/revoke-sessions`
- `GET /api/outlook/accounts/{email}/risky-users`
- `POST /api/outlook/accounts/{email}/dismiss-risk`

## 5. Outlook 协议接口

- `POST /api/outlook/protocol/test-login`
- `POST /api/outlook/protocol/list-proofs`
- `POST /api/outlook/protocol/bind`
- `POST /api/outlook/protocol/replace`

当前单次协议向导使用静态验证码字段 `static_code`。

## 6. 渠道与资源池接口

### 渠道

- `GET /api/outlook/channels`
- `POST /api/outlook/channels`
- `PUT /api/outlook/channels/{channel_id}`
- `POST /api/outlook/channels/{channel_id}/accounts/bind`
- `POST /api/outlook/channels/{channel_id}/resources/bind`
- `GET /api/outlook/channels/stats`

### 资源池

- `GET /api/outlook/resources/aux-emails`
- `POST /api/outlook/resources/aux-emails`
- `POST /api/outlook/resources/aux-emails/import`
- `PUT /api/outlook/resources/aux-emails/{resource_id}`
- `POST /api/outlook/resources/aux-emails/{resource_id}/rotate`

## 7. 任务中心接口

- `GET /api/outlook/tasks`
- `GET /api/outlook/tasks/{task_id}`
- `POST /api/outlook/tasks/{task_id}/cancel`
- `POST /api/outlook/tasks/{task_id}/retry`
- `GET /api/outlook/tasks/events/stream?token=<jwt>`

## 8. 响应约定

绝大多数接口遵循：

```json
{
  "success": true,
  "message": "optional",
  "data": {}
}
```

业务失败时通常仍返回：

```json
{
  "success": false,
  "message": "error message"
}
```

认证或系统异常时返回标准 HTTP 错误码。

## 9. 当前注意事项

- `/api/outlook/*` 接口依赖 feature flags
- `/api/outlook/tasks/events/stream` 在 Redis 不可达时会降级返回 warning 事件
- 旧 `/api/accounts/pick` 已兼容渠道模型，但保留旧标签语义

