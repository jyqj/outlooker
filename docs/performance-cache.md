# 缓存与资源性能说明

当前性能链路分为四层：

- 账户缓存：`AccountCacheService`
- 邮件缓存：`email_cache` / `email_cache_meta`
- 数据库执行资源：SQLite WAL + 延迟创建的专用线程池
- 前端静态资源：Vite 路由分包 + 显式 HTTP 缓存策略

## 1. 邮件缓存写入

IMAP 一次拉取多封邮件后，使用 `cache_emails()` 在同一数据库连接和事务中批量 upsert，随后只执行一次容量淘汰。单封邮件入口 `cache_email()` 保留为兼容门面。

这一设计避免了旧链路中每封邮件各自执行以下开销：

1. 创建 SQLite 连接；
2. 开启并提交事务；
3. 执行一次容量扫描与删除。

缓存 feed 与 retention 查询使用专用索引；由 `PRIMARY KEY` / `UNIQUE` 已覆盖的重复索引会在初始化时清理，降低写放大。

## 2. SQLite 与线程资源

- WAL 只在数据库初始化阶段设置，不再为每个连接重复切换；
- 每个连接启用 5 秒 `busy_timeout`，降低短暂写竞争导致的失败；
- 数据库线程池在首个异步操作时创建，CLI 导入、测试收集等只读启动路径不会预先占用线程；
- 应用关闭时在线程外等待 executor 退出，避免阻塞事件循环。

## 3. 前端资源交付

- 公共验证码页面保持在首包中，登录页、后台仪表盘和 Outlook 工作台按路由异步加载；
- Sentry SDK 仅在配置 `VITE_SENTRY_DSN` 时动态加载；
- `/assets/*` 的 Vite 内容哈希文件使用一年 immutable 缓存；
- `index.html` 使用 `no-cache`，确保发布后能及时发现新资源清单；
- `frontend/public` 中复制到构建根目录的文件（例如 `/favicon.svg`）会作为真实文件返回，而不是误回退到 SPA HTML。

## 4. 建议观察项

- `/api/system/metrics`
- `email_manager.cache_hit_rate`
- `email_manager.email_cache.total_messages`
- 邮件拉取日志中的总耗时与每封平均耗时
- 浏览器 Network 面板中的入口 chunk、后台 route chunk 和 `Cache-Control`

## 5. 验证命令

```bash
# 后端质量与测试
ruff check backend/app tests/backend
mypy backend/app --config-file mypy.ini
cd backend && pytest

# 前端必须验证真实生产构建，而不只是 typecheck
npm --prefix frontend run typecheck
npm --prefix frontend run build
npm --prefix frontend run test -- --coverage

# 邮件缓存写入路径对比（逐封事务 vs 批量事务）
python3 scripts/benchmarks/benchmark_email_cache_writes.py --counts 10 50 100 --repeats 10

# 大规模 SQLite 查询基准
python3 scripts/benchmarks/benchmark_email_cache.py --sizes 100000 500000 1000000
```
