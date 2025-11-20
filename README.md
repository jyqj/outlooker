# Outlook Manager

单仓库包含：

- `backend/`：FastAPI 应用（`app/` 包）、测试、配置、脚本。
- `frontend/`：React + Vite 管理后台与验证码工具。
- `infra/`：Dockerfile、Compose、部署脚本。
- `docs/`：API 文档、安全指南、快速开始等。
- `data/`：运行时生成的数据库、日志、静态资源（默认被 `.gitignore` 排除）。
- `scripts/`：在宿主机运行的维护/安全脚本，自动引用 `backend` 包。

## 开发入口

| 模块 | 命令 |
| --- | --- |
| 后端 | `cd backend && python -m app.mail_api web` |
| 前端 | `cd frontend && npm install && npm run dev` |
| 测试 | `cd backend && pytest` |

环境变量通过项目根目录的 `.env` 管理（参考 `.env.example`），后端 `app.settings` 会自动加载 `PROJECT_ROOT/.env`。

更多细节：

- [docs/BACKEND_README.md](docs/BACKEND_README.md) – 后端功能说明
- [docs/BACKEND_QUICKSTART.md](docs/BACKEND_QUICKSTART.md) – 快速开始
- [docs/API_DOCUMENTATION.md](docs/API_DOCUMENTATION.md) – REST API
- [docs/LOGIN_SECURITY.md](docs/LOGIN_SECURITY.md) – 登录安全/频控
- [docs/QUICK_TEST_REFERENCE.md](docs/QUICK_TEST_REFERENCE.md) – 自动化安全检查
- [scripts/run_smoke_tests.py](scripts/run_smoke_tests.py) – 部署后冒烟脚本

部署可参考 `infra/deploy.sh` 或直接 `docker compose`（`infra/docker-compose.yml`）。
