# 维护与日常运维

## 1. 依赖安装

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

## 2. 常用维护脚本

- `scripts/maintenance/backfill_outlook_accounts.py`
- `scripts/maintenance/encrypt_existing_accounts.py`
- `scripts/maintenance/cleanup_email_cache.py`
- `scripts/maintenance/view_login_audit.py`
- `scripts/run_smoke_tests.py`

## 3. 依赖升级建议

- Python 依赖先在 `requirements-dev.txt` 环境中验证测试
- 前端依赖升级后至少跑：
  - `npm run typecheck`
  - `npm run test`
  - Playwright 新工作台用例

## 4. Worker / Redis

- `FEATURE_OUTLOOK_WORKER_ENABLED=true` 时必须有 Redis
- Worker 启动命令：

```bash
cd backend
celery -A app.workers.celery_app.celery_app worker --loglevel=INFO
```

## 5. 数据迁移

数据库结构统一由迁移框架管理，不手工改表。

新增结构前建议：

1. 备份 `data/outlook_manager.db`
2. 新增 migration
3. 跑测试
4. 再在目标环境启动应用

