[← 返回文档目录](./README.md)

# Outlooker 快速开始指南

本文档提供 Outlooker 后端系统的快速上手指南，帮助开发者在 5 分钟内启动项目。

## 1. 环境准备

1. 安装依赖
   ```bash
   pip install -r backend/requirements.txt
   cd frontend && npm install
   ```
2. 复制 `.env.example` 到项目根目录，设置 CLIENT_ID、JWT_SECRET_KEY、DATA_ENCRYPTION_KEY 以及管理员账号等必填项。
3. 首次运行会在 `data/outlook_manager.db` 中创建数据库。

## 2. 日常开发

| 模块 | 命令 | 说明 |
| --- | --- | --- |
| 后端 API | `cd backend && python -m app.mail_api web` | 启动 FastAPI，监听 `http://localhost:5001` |
| React 前端 | `cd frontend && npm run dev` | Vite 开发模式，端口 `5173` |
| 前端构建 | `npm run build` | 构建产物写入 `data/static/`（git 忽略） |

生产或集成环境可使用 Docker：

```bash
cd docker
docker-compose up --build -d
```

`docker-compose.yml` 会自动读取项目根目录 `.env`。

## 3. 管理后台速览

- 登录地址：`/admin/login`
- 功能：
  - 账户列表（分页、搜索）
  - **增强的分页功能**：
    - 每页显示数量选择（10/20/50/100）
    - 智能页码导航（带省略号）
    - 快速跳转到指定页
    - 总记录数统计
  - 标签维护（点击“管理标签”即可编辑）
  - 批量导入/导出
  - 系统配置（邮件获取条数）
  - 系统指标（缓存命中、IMAP 复用、警告等）
  - 邮件查看（完整正文 + 验证码提取）

**验证码工具**（根路径 `/`）：
- 简化版，仅支持数据库账户模式
- 输入邮箱地址 → 获取最新验证码
- 自动提取邮件中的 4~6 位验证码
- 一键复制功能
- 已移除临时账户模式（Refresh Token 输入）

## 4. 常见任务

- **新增账户**：在后台或通过 `POST /api/accounts`，系统会自动加密 refresh_token。
- **更新系统配置**：后台页面直接修改，或调用 `POST /api/system/config`。
- **标签管理**：后台按钮或 API `POST /api/account/{email}/tags`。
- **临时拉取邮件**：调用 `/api/temp-messages`，支持 `page/page_size/search/folder`。

## 5. 测试与诊断

```bash
cd backend
pytest
```

- 覆盖 API、服务层缓存、导入逻辑与新账户接口。
- 测试会清空数据库数据，执行前请确认不要在生产库运行。

常见问题：

| 症状 | 排查 |
| --- | --- |
| `JWT_SECRET_KEY 未配置` | 检查 `.env` 是否正确加载 |
| Legacy Token 验证失败 | 默认为关闭，如需启用在 `.env` 中设置 `ENABLE_LEGACY_ADMIN_TOKEN=true` 并自定义 `LEGACY_ADMIN_TOKEN` |
| 删除账户返回失败 | 可能未清理构建产物，确保前端 `npm run build` 后再启动 |
| Docker 启动失败 | 确认 `.env` 已与 compose 挂载，且 `npm run build` 已执行 |

安全脚本请参考 [安全机制](./security.md)，自动化安全巡检见 [测试指南](./testing.md)。
