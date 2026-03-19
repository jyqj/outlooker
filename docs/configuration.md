# 配置说明

Outlooker 使用根目录 `.env` 作为主要配置入口。

## 1. 基础配置

```env
APP_ENV=development
ALLOWED_ORIGINS=http://localhost:5173,http://localhost:5001
DATABASE_PATH=data/outlook_manager.db
LOGS_DIR=data/logs
STATIC_DIR=data/static
LOG_LEVEL=INFO
```

## 2. 认证与安全

```env
ADMIN_USERNAME=admin
ADMIN_PASSWORD=change-me
JWT_SECRET_KEY=replace-me
DATA_ENCRYPTION_KEY=replace-me
PUBLIC_API_TOKEN=replace-me
ACCESS_TOKEN_EXPIRE_MINUTES=1440
REFRESH_TOKEN_EXPIRE_DAYS=7
```

## 3. Outlook / IMAP

```env
CLIENT_ID=replace-with-azure-client-id
TOKEN_URL=https://login.microsoftonline.com/consumers/oauth2/v2.0/token
IMAP_SERVER=outlook.live.com
IMAP_PORT=993
INBOX_FOLDER_NAME=INBOX
JUNK_FOLDER_NAME=Junk
```

## 4. Feature Flags

```env
FEATURE_OUTLOOK_GRAPH_ENABLED=false
FEATURE_OUTLOOK_PROTOCOL_ENABLED=false
FEATURE_OUTLOOK_WORKER_ENABLED=false
FEATURE_OUTLOOK_CHANNELS_ENABLED=false
FEATURE_OUTLOOK_RESOURCES_ENABLED=false
FEATURE_OUTLOOK_BROWSER_FALLBACK_ENABLED=false
```

建议启用顺序见 [outlook-rollout-checklist.md](./outlook-rollout-checklist.md)。

## 5. Redis / Celery

```env
REDIS_URL=redis://localhost:6379/0
REDIS_PUBSUB_CHANNEL=bind_task_updates
CELERY_BROKER_URL=redis://localhost:6379/1
CELERY_RESULT_BACKEND=redis://localhost:6379/2
```

## 6. 前端

前端主要依赖以下变量：

```env
VITE_PUBLIC_API_TOKEN=dev-public-token-change-me
VITE_API_BASE=
```

在开发环境通常不需要显式设置 `VITE_API_BASE`，Vite 会通过代理把 `/api` 转发到 `5001`。

## 7. 常见建议

- 生产环境必须替换所有默认密钥与密码
- `FEATURE_OUTLOOK_WORKER_ENABLED=true` 时，必须同时有 Redis 和 Celery Worker
- 协议链路启用前，先确认日志脱敏和资源池配置已就绪

