# 架构说明

## 1. 总览

Outlooker 当前是一个三层能力平台：

- 邮箱池与验证码：旧 `accounts / messages / tags`
- Outlook 资产管理：`/api/outlook/accounts*`
- 协议与渠道：`/api/outlook/protocol*`、`/api/outlook/channels*`、`/api/outlook/resources*`、`/api/outlook/tasks*`

## 2. 后端分层

```text
routers
  ├── 旧域：accounts / emails / tags / system / auth / batch / dashboard
  └── 新域：outlook_accounts / outlook_protocol / outlook_channels / outlook_resources / outlook_tasks

services
  ├── outlook/
  │   ├── graph.py
  │   ├── graph_token_service.py
  │   ├── protocol.py
  │   ├── protocol_parsers.py
  │   ├── protocol_code_provider.py
  │   └── fingerprint.py
  ├── channeling/
  └── tasks/

db
  ├── manager.py
  ├── accounts.py / tags.py / audit.py / system_config.py
  ├── outlook_accounts.py
  ├── oauth_tokens.py
  ├── channeling.py
  ├── protocol_tasks.py
  └── account_operations.py
```

## 3. 数据层

当前核心表：

- `accounts`
- `tags`
- `account_tag_relations`
- `outlook_accounts`
- `oauth_configs`
- `oauth_tokens`
- `account_capabilities`
- `account_profiles_cache`
- `account_security_methods_snapshot`
- `aux_email_resources`
- `channels`
- `channel_account_relations`
- `channel_resource_relations`
- `allocation_leases`
- `protocol_tasks`
- `protocol_task_steps`
- `account_operation_audit`

所有结构变更统一通过 [backend/app/migrations/__init__.py](/Users/jin/Desktop/outlooker/backend/app/migrations/__init__.py) 管理。

## 4. 前端结构

前端主要由两部分构成：

- 旧后台：`dashboard / tags / settings / audit`
- 新工作台：`outlook/accounts / tasks / resources / channels`

新增工作台页面：

- `OutlookAccountsPage`
- `OutlookAccountDetailPage`
- `OutlookTasksPage`
- `AuxEmailPoolPage`
- `ChannelConsolePage`

## 5. 异步架构

任务链路依赖：

- Redis：broker + pub/sub
- Celery：后台任务执行
- FastAPI：同步 API + SSE 事件流

当前 worker 任务主要是：

- `protocol_bind_secondary`
- `protocol_rebind_secondary`

## 6. 运行形态

### API

```bash
cd backend
python -m app.mail_api web
```

### Worker

```bash
cd backend
celery -A app.workers.celery_app.celery_app worker --loglevel=INFO
```

### Frontend

```bash
cd frontend
npm run dev
```

### Docker

```bash
cd docker
docker-compose up -d
```

## 7. 设计原则

- 旧接口优先兼容，不强制前端一次切换
- 新能力按领域拆层，不继续堆到旧 `models.py`
- Graph、Protocol、Channeling、Tasks 四个新域彼此独立
- 所有敏感操作记录审计，所有敏感字段默认脱敏

