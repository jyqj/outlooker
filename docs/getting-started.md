# 快速开始

## 1. 环境要求

- Python `3.12+`
- Node.js `18+`
- npm `10+`
- Redis（启用 worker / 任务中心时）

## 2. 安装依赖

### 后端

```bash
cd backend
pip install -r requirements-dev.txt
```

### 前端

```bash
cd frontend
npm install
```

## 3. 配置 `.env`

从根目录复制：

```bash
cp .env.example .env
```

开发环境最低可用配置：

```env
APP_ENV=development
ADMIN_USERNAME=admin
ADMIN_PASSWORD=admin123
JWT_SECRET_KEY=replace-me
DATA_ENCRYPTION_KEY=replace-me
PUBLIC_API_TOKEN=replace-me
```

启用 Outlook 增强能力时：

```env
FEATURE_OUTLOOK_GRAPH_ENABLED=true
FEATURE_OUTLOOK_PROTOCOL_ENABLED=true
FEATURE_OUTLOOK_CHANNELS_ENABLED=true
FEATURE_OUTLOOK_RESOURCES_ENABLED=true
FEATURE_OUTLOOK_WORKER_ENABLED=true
```

## 4. 启动服务

### 只跑基础后台

```bash
cd backend
python -m app.mail_api web

cd ../frontend
npm run dev
```

### 启用任务中心

```bash
redis-server

cd backend
celery -A app.workers.celery_app.celery_app worker --loglevel=INFO
```

## 5. 访问路径

- 前端：`http://localhost:5173`
- 后端：`http://localhost:5001`
- API 文档：`http://localhost:5001/docs`
- 管理后台：`http://localhost:5173/admin`

## 6. 首次检查

建议依次执行：

```bash
# 类型检查
npm --prefix frontend run typecheck

# 前端单测
npm --prefix frontend run test

# 后端测试
cd backend && pytest

# 冒烟测试
python3 scripts/run_smoke_tests.py
```

## 7. Docker

```bash
cd docker
docker-compose up -d
```

这会启动：

- API
- Redis
- Worker

