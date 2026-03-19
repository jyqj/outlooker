# Outlooker

现代化的 Outlook 资产管理、验证码提取与协议绑定平台。

## 项目定位

Outlooker 现在包含三条主线能力：

- 邮箱池与验证码：邮箱导入、标签、随机取号、邮件查看、验证码提取
- Outlook 资产管理：OAuth Token、资料、密码、身份验证方式、会话、风险、区域与邮箱设置
- 协议与渠道：纯协议登录、OTC 验证、恢复邮箱绑定/换绑、任务中心、辅助邮箱资源池、渠道化分配

## 技术栈

- 后端：FastAPI + Python 3.12 + SQLite
- 前端：React 19 + TypeScript + Vite + TanStack Query
- 异步：Redis + Celery
- 自动化测试：pytest + Vitest + Playwright

## 代码结构

```text
outlooker/
├── backend/
│   ├── app/
│   │   ├── auth/                # JWT、加密、OAuth
│   │   ├── core/                # 异常、限流、指标、中间件
│   │   ├── db/                  # SQLite mixin 层
│   │   ├── migrations/          # 数据库迁移
│   │   ├── routers/             # API 路由
│   │   ├── schemas/             # 新领域请求模型
│   │   ├── services/
│   │   │   ├── channeling/      # 渠道、租约、资源池
│   │   │   ├── outlook/         # Graph、Protocol、Binder
│   │   │   └── tasks/           # 任务状态与事件
│   │   ├── workers/             # Celery Worker
│   │   └── mail_api.py          # FastAPI 入口
│   └── requirements*.txt
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   └── outlook/         # Outlook 工作台组件
│   │   ├── pages/
│   │   │   ├── dashboard/
│   │   │   └── outlook/         # 账户、任务、资源池、渠道控制台
│   │   ├── lib/
│   │   ├── i18n/
│   │   └── types/
│   └── playwright.config.ts
├── docker/
├── docs/
├── scripts/
└── tests/
```

## 核心入口

- 前端首页：`/`
- 管理后台：`/admin`
- Outlook 账户工作台：`/admin/outlook/accounts`
- 任务中心：`/admin/outlook/tasks`
- 资源池：`/admin/outlook/resources`
- 渠道控制台：`/admin/outlook/channels`
- OpenAPI：`/docs`

## 快速开始

### 1. 安装依赖

```bash
cd backend
pip install -r requirements-dev.txt

cd ../frontend
npm install
```

### 2. 配置环境变量

复制根目录 `.env.example` 为 `.env`，至少配置：

```env
APP_ENV=development
ADMIN_USERNAME=admin
ADMIN_PASSWORD=admin123
JWT_SECRET_KEY=replace-me
DATA_ENCRYPTION_KEY=replace-me
PUBLIC_API_TOKEN=replace-me
```

如果要启用 Outlook 增强能力，还需要打开对应 feature flags：

```env
FEATURE_OUTLOOK_GRAPH_ENABLED=true
FEATURE_OUTLOOK_PROTOCOL_ENABLED=true
FEATURE_OUTLOOK_CHANNELS_ENABLED=true
FEATURE_OUTLOOK_RESOURCES_ENABLED=true
FEATURE_OUTLOOK_WORKER_ENABLED=true
```

### 3. 启动后端

```bash
cd backend
python -m app.mail_api web
```

后端默认监听 `http://localhost:5001`。

### 4. 启动前端

```bash
cd frontend
npm run dev
```

前端默认监听 `http://localhost:5173`，并代理 `/api` 到 `5001`。

### 5. 启动 Worker

启用任务中心时，需要同时启动 Redis 和 Celery Worker。

```bash
redis-server

cd backend
celery -A app.workers.celery_app.celery_app worker --loglevel=INFO
```

### 6. Docker

```bash
cd docker
docker-compose up -d
```

当前 `docker-compose` 会启动：

- `outlook-mail-system`
- `outlook-mail-worker`
- `redis`

## 常用命令

```bash
# 后端测试
cd backend && pytest

# 前端类型检查
npm --prefix frontend run typecheck

# 前端单测
npm --prefix frontend run test

# Playwright E2E
cd frontend && npm exec -- playwright test

# 冒烟测试
python3 scripts/run_smoke_tests.py

# Outlook 资产回填
python3 scripts/maintenance/backfill_outlook_accounts.py
```

## 当前验证结果

当前仓库已经完成以下验证：

- 后端新增模块测试通过
- 受影响旧路由测试通过
- 前端 `typecheck` 通过
- 前端 Vitest 全通过
- 新工作台 Playwright 在 `chromium / firefox / webkit / mobile` 通过
- smoke script 通过

## 文档入口

- [文档目录](docs/README.md)
- [快速开始](docs/getting-started.md)
- [架构说明](docs/architecture.md)
- [API 参考](docs/api-reference.md)
- [配置说明](docs/configuration.md)
- [测试指南](docs/testing.md)
- [安全机制](docs/security.md)
- [灰度上线清单](docs/outlook-rollout-checklist.md)

