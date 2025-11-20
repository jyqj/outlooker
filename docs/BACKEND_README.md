# Outlooker 后端架构文档

现代化的 Outlook 邮件管理平台后端系统，采用 FastAPI + SQLite + Python 3.12 构建。系统提供完整的邮件查看、账户管理、验证码提取、安全认证等功能，并内置数据加密、频率限制、审计日志等企业级安全特性。

## 功能概览

- **统一配置**：所有敏感参数通过 `.env` 管理，支持 Docker / 本地一致的加载逻辑。
- **账户管理**：支持列表搜索、分页、导入、导出、新增、更新、删除，以及标签维护。
- **邮件查看**：一次性获取完整正文，接口支持分页、模糊搜索、文件夹切换，前端可直接提取验证码。
- **系统洞察**：后台可实时查看缓存命中率、IMAP 客户端复用、警告提示等运行指标。
- **缓存控制**：提供后台按钮 + API `/api/system/cache/refresh`，可一键刷新账户与邮件缓存，避免脏数据。
- **安全增强**：默认强制 JWT 登录，Legacy Token 需显式开启；refresh_token 与密码自动加密，登录频率限制 + 审计日志。

## 目录结构（节选）

```
.
├── backend/
│   ├── app/              # FastAPI 应用及业务代码
│   ├── configs/          # system_config.json、token_config 示例等
│   └── tests/            # Pytest 用例
├── frontend/             # React + Vite 前端
├── infra/                # Dockerfile、compose、部署脚本
├── data/                 # 运行期数据 (logs/static/outlook_manager.db)
├── scripts/              # 运维脚本（依赖 backend 包）
└── docs/                 # API 文档、安全指南、快速开始
```

## 数据库迁移

自 v2.2 起内置 `app/migrations` 目录来管理 schema 变更：

- 应用启动、`pytest` 运行或 CLI 执行前会自动检查 `schema_migrations` 表并执行新的迁移。
- 如需新增字段/索引，请编写 `register_migration` 装饰的函数并提交；避免直接手工执行 SQL。
- 任何数据库变更前建议备份 `data/outlook_manager.db`，需要回滚时删除对应版本记录后重新启动即可。

## 环境准备

1. **安装依赖**
   ```bash
   pip install -r backend/requirements.txt
   cd frontend && npm install
   ```

2. **配置环境变量**
   ```bash
   cp .env.example .env   # 根目录
   # 需填写 CLIENT_ID / JWT_SECRET_KEY / DATA_ENCRYPTION_KEY
   # 生产环境务必设置 ADMIN_USERNAME / ADMIN_PASSWORD
   ```

3. **初始化数据目录**
   - 默认数据库位于 `data/outlook_manager.db`（首次启动自动创建）。
   - 前端构建后的静态文件与日志也会写入 `data/static`、`data/logs`。

## 本地开发

### 后端
```bash
cd backend
python -m app.mail_api web
# FastAPI 监听 http://localhost:5001
```

### 前端
```bash
cd frontend
npm run dev        # 默认 http://localhost:5173
npm run build      # 产物输出到 data/static
```

### Docker
```bash
cd infra
./deploy.sh build
./deploy.sh start
```
Compose 会使用根目录 `.env`，同时挂载 `data/` 与 `backend/configs/`。

## 管理后台

- `http://localhost:5001/admin/login`：JWT 登录。
- 登录后可进行：
  - 账户搜索 / 分页；
  - 批量导入 / 导出；
  - 标签维护（点击“管理标签”即可快速编辑）；
  - 系统配置（邮件拉取限制）；
  - 运行指标（缓存命中、IMAP 复用、警告等）；
  - 缓存管理（“刷新缓存”按钮触发 `/api/system/cache/refresh`，同时清空邮件缓存与账户缓存）。

## 接口说明

完整 API 文档见 `API_DOCUMENTATION.md`，重点更新：

- `GET /api/messages`: 新增 `page`, `page_size`, `folder`, `search` 参数，返回 `{items, total, page, page_size, folder}`。
- `POST /api/temp-messages`: 同步支持分页/搜索。
- 账户 CRUD：
  - `POST /api/accounts`
  - `GET /api/account/{email}`
  - `PUT /api/account/{email}`
  - `DELETE /api/account/{email}`
- 系统配置 PATCH：`POST /api/system/config`。
- 缓存刷新：`POST /api/system/cache/refresh`。

所有受保护接口均需要 `Authorization: Bearer <token>`。

## 测试

```bash
cd backend
pytest
```

- 覆盖 API、服务层缓存、导入逻辑及新账户接口。
- 默认测试配置使用 `.env.example` 中的安全占位值。

## 常用脚本

- `scripts/test_security_improvements.py`：检查 JWT 密钥、管理员密码、Legacy Token、CORS、日志与加密。
- `scripts/encrypt_existing_accounts.py`：对已有账户执行加密迁移。
- `scripts/test_rate_limiting.py`、`docs/LOGIN_SECURITY.md`：登陆安全验证。
- `scripts/run_smoke_tests.py`：CI/部署后调用 `/api/admin/login → /api/accounts → /api/system/metrics` 的冒烟脚本，可通过环境变量注入管理员密码或现有 JWT。

## 注意事项

- `.gitignore` 已排除数据库、日志与构建产物，请在部署前运行 `npm run build` 生成最新静态资源。
- 默认禁用 Legacy 管理 Token，如需兼容旧客户端，请在 `.env` 中设置 `ENABLE_LEGACY_ADMIN_TOKEN=true` 并自定义 `LEGACY_ADMIN_TOKEN`。
- `get_refresh_token.py` 依赖本地浏览器（DrissionPage），仅在开发机运行，服务器部署请直接配置 refresh_token。

## 反馈

遇到问题请：
1. 检查 `.env` 是否完整；
2. 查看 `logs/login_audit.log` 与 FastAPI 日志；
3. 运行 `pytest` 与 `npm run build` 验证；
4. 更新 `API_DOCUMENTATION.md`、`README` 后再提交。

祝使用顺利！
