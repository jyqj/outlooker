# 灰度上线清单

## 1. 建议顺序

1. `FEATURE_OUTLOOK_GRAPH_ENABLED=true`
2. `FEATURE_OUTLOOK_PROTOCOL_ENABLED=true`
3. `FEATURE_OUTLOOK_CHANNELS_ENABLED=true`
4. `FEATURE_OUTLOOK_RESOURCES_ENABLED=true`
5. `FEATURE_OUTLOOK_WORKER_ENABLED=true`
6. `FEATURE_OUTLOOK_BROWSER_FALLBACK_ENABLED=true`

## 2. 每阶段检查

### Graph

- `/api/outlook/accounts`
- `/api/outlook/accounts/batch-refresh`
- profile / mailbox / regional settings

### Protocol

- `test-login`
- `list-proofs`
- 单次 bind / replace

### Channels / Resources

- 渠道 CRUD
- 资源池 CRUD
- 账户绑定 / 资源绑定
- 旧 `/api/accounts/pick` 兼容

### Worker

- Redis
- Celery
- `/api/outlook/tasks`
- SSE

## 3. 回退

- 优先关 feature flag
- 数据库结构回退依赖备份，不做 down migration

