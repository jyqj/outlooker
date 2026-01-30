# Outlooker API 契约与运维说明

该文档面向需要同时维护前后端的开发者，快速对齐 **Outlooker** 项目的接口契约与常见运维操作。

若需完整 API 说明，请参考：
- [API 完整文档](./API_DOCUMENTATION.md)
- [后端快速开始](./BACKEND_QUICKSTART.md)

## 1. 核心 API 契约

| 功能 | Endpoint | Method | 认证 | 关键请求字段 | 响应数据(data) |
| --- | --- | --- | --- | --- | --- |
| 账户分页 | `/api/accounts/paged` | GET | Bearer | `page`(>=1), `page_size`(<=100), `q`(模糊搜索) | `{ items: [{ email }], total, page, page_size }`
| 标签拉取 | `/api/accounts/tags` | GET | Bearer | - | `{ tags: string[], accounts: { [email]: string[] } }`
| 标签写入 | `/api/account/{email}/tags` | POST | Bearer | body: `{ email, tags: string[] }` | `{ success: boolean, message }`，成功后需刷新缓存
| 账户导入 | `/api/import` | POST | Bearer | `{ accounts: ImportAccountData[], merge_mode: "update"\|"skip"\|"replace" }` | `ImportResult`（计数 + details）
| 文本解析 | `/api/parse-import-text` | POST | Bearer | `{ text }` | `{ parsed_count, error_count, accounts, errors[] }`
| 配置读取 | `/api/system/config` | GET | Bearer | - | `{ email_limit }`（如需扩展，前后端共用同名字段）
| 配置更新 | `/api/system/config` | POST | Bearer | `{ email_limit }` | `{ success, message }`；写入 DB（首次启动可从 `system_config.json` 引导默认值）
| 指标获取 | `/api/system/metrics` | GET | Bearer | - | `{ email_manager: { cache_hit_rate, email_cache, ... }, ... }`
| 缓存刷新 | `/api/system/cache/refresh` | POST | Bearer | - | `{ success, message }`；触发 `EmailManager.invalidate_accounts_cache()` 并清空邮件缓存
| 邮件列表 | `/api/messages` | GET | `X-Public-Token` | `email`，分页：`page`，`page_size`，`folder`，可选：`search`，`refresh` | `{ items: EmailMessage[], total?, page, page_size }`
| 临时查询 | `/api/temp-messages` | POST | `X-Public-Token` | `{ email, refresh_token, page, page_size, search }` | 与 `/api/messages` 数据结构一致（`debug/internal`：前端不使用）
| 连接测试 | `/api/test-email` | POST | `X-Public-Token` | `{ email, refresh_token? }` | 最新 1 封邮件（或 `null`）；`debug/internal`
| 删除邮件 | `/api/email/{email}/{message_id}` | DELETE | Bearer | - | `{ success, message }`（管理后台使用：删除本地缓存）
| 标记已读 | `/api/email/{email}/{message_id}/read` | POST | Bearer | - | `{ success, message }`（`deprecated/internal`：前端未使用）

### ImportAccountData / ImportResult

- `ImportAccountData` 字段：`email`、`password?`、`client_id?`、`refresh_token`。
- `ImportResult` 字段：`success`、`total_count`、`added_count`、`updated_count`、`skipped_count`、`error_count`、`details[]`、`message`。
- `details` 内部结构：`{ action: "added"\|"updated"\|"skipped"\|"error", email, message }`，供前端展示与下载。

### 响应一致性约定

- `success`：布尔值，默认视为 `true`，除显式 `false` 外一律当成功处理。
- `message`：后端统一使用 `messages.py` 中的常量。前端 `useApiAction` 已根据 `success` 字段自动处理 toast。
- `data`：若返回列表，字段命名统一为 `items`；分页返回必须包含 `page`、`page_size`、`total`。

## 2. 系统配置与缓存运维

### 2.1 配置存储

- 默认路径：`backend/configs/system_config.json`（可通过 `app.services.SYSTEM_CONFIG_FILE` monkeypatch 覆盖）。
- 运行时配置源：数据库 `system_config` 表（当 DB 缺失 key 时，才会读取文件/默认值并写回 DB 作为一次性引导）。
- 所有写入必须调用 `services.set_system_config_value`，该函数会：
  1. 重新计算并校验值（目前仅限制 `email_limit` 范围 1~MAX_EMAIL_LIMIT）。
  2. 写入数据库，供多节点读取（不再写入 JSON 文件）。

### 2.2 缓存刷新

- `EmailManager` 缓存：通过 `/api/system/cache/refresh` 或后端 `email_manager.invalidate_accounts_cache()` 触发。
- 邮件缓存（SQLite `email_cache` + `email_cache_meta` 表）：`/api/messages` 会优先读取本地缓存，并按 `EMAIL_CACHE_TTL_SECONDS` 控制 IMAP 刷新频率；同一端点会调用 `DatabaseManager.reset_email_cache()` 清空缓存；另有脚本 `scripts/cleanup_email_cache.py` 可按天清理。
- 指标观测：`email_manager.get_metrics()` 会把快照写入 `system_metrics`，可通过 `/api/system/metrics` 查看命中率、缓存大小等数据。

### 2.3 常见维护脚本

| 脚本 | 用途 | 注意事项 |
| --- | --- | --- |
| `scripts/encrypt_existing_accounts.py` | 将旧明文账户迁移为加密存储 | 运行前需设置 `DATA_ENCRYPTION_KEY`，并备份数据库 |
| `scripts/cleanup_email_cache.py` | 清理过期邮件缓存（默认 30 天） | 可通过参数指定 `--days`；建议配合定时任务 |
| `scripts/cleanup_email_cache.py --dry-run` | 仅查看将被删除的记录数 | 不会修改数据库 |

### 2.4 监控与告警建议

- **登录失败计数**：`rate_limiter` 通过 SQLite 记录，可监控 `login_audit` 表，超过阈值触发告警。
- **邮箱连接**：`EmailManager` 日志包含 `开始获取 {email}` 及异常信息；建议收集 `logger` 输出到集中式日志系统。
- **系统配置漂移**：定期比较 `system_config` 表与配置文件，或直接依赖此服务层读取逻辑。

## 3. 对前端的对齐建议

1. 前端任何分页查询都沿用本表字段（`page`/`page_size`/`total`），React Query key 已加入分页参数，避免缓存串行。
2. `useApiAction` 在遇到业务失败或网络异常时会通过 `logError` 在 DEV 环境记录具体 payload/错误，生产环境不输出 `console`。
3. `MESSAGES` 常量应作为唯一来源（例如导出、标签、系统配置等场景已经对齐）。新增接口时先在 `constants.js` 登记必要的提示文案。

---

> 本文为初稿，未来可扩展：
> - 新增 E2E 场景示例（例如批量导入后校验标签覆盖）
> - 更细粒度的错误码表，与 `messages.py` 中的定义同步
> - 将运维脚本封装为 Makefile/Invoke 任务，便于 CI/CD 中引用
