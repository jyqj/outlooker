# Outlooker

<div align="center">

**现代化的 Outlook 邮件管理与验证码提取平台**

[![Python](https://img.shields.io/badge/Python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-green.svg)](https://fastapi.tiangolo.com/)
[![React](https://img.shields.io/badge/React-19.0-61dafb.svg)](https://reactjs.org/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

</div>

---

## 📖 项目简介

**Outlooker** 是一个功能强大的 Outlook 邮件管理系统，专为高效管理多个邮箱账户、快速提取验证码而设计。系统采用现代化技术栈，提供完善的安全机制和友好的用户界面。

### ✨ 核心特性

- 🔐 **安全可靠**：JWT 认证、数据加密存储、登录频率限制、审计日志
- 📧 **邮件管理**：支持多账户、分页查询、文件夹切换、模糊搜索
- 🎯 **验证码提取**：自动识别并提取邮件中的 4-6 位验证码
- 👥 **账户管理**：批量导入/导出、标签分类、账户搜索
- 📊 **系统监控**：缓存命中率、IMAP 连接复用、运行指标统计
- 🎨 **现代 UI**：基于 React + Tailwind CSS，响应式设计
- 🐳 **容器化部署**：提供 Docker 和 Docker Compose 配置

### 🏗️ 技术架构

```
┌─────────────────────────────────────────────────────────┐
│                     前端层 (Frontend)                    │
│    React 19 + Vite + TailwindCSS + React Query          │
└────────────────────┬────────────────────────────────────┘
                     │ REST API (JWT Auth)
┌────────────────────▼────────────────────────────────────┐
│                   后端层 (Backend)                       │
│        FastAPI + Pydantic + Python 3.12                 │
├─────────────────────────────────────────────────────────┤
│  • JWT 认证        • 邮件服务       • 账户管理          │
│  • 频率限制        • 缓存管理       • 数据加密          │
└────────────────────┬────────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────────┐
│                  数据层 (Storage)                        │
│        SQLite + 文件缓存 + 审计日志                     │
└─────────────────────────────────────────────────────────┘
```

## 📁 项目结构

```
outlooker/
├── backend/              # 后端服务
│   ├── app/             # FastAPI 应用核心
│   │   ├── routers/     # API 路由（账户、邮件、系统、认证）
│   │   ├── services/    # 业务逻辑层
│   │   ├── migrations/  # 数据库迁移脚本
│   │   ├── models.py    # 数据模型
│   │   ├── security.py  # 加密与安全
│   │   └── jwt_auth.py  # JWT 认证
│   ├── configs/         # 配置文件
│   ├── tests/           # 单元测试和集成测试
│   └── requirements.txt # Python 依赖
├── frontend/            # 前端应用
│   ├── src/
│   │   ├── components/  # React 组件
│   │   ├── pages/       # 页面组件
│   │   ├── lib/         # 工具库和 Hooks
│   │   └── main.jsx     # 应用入口
│   └── package.json     # Node.js 依赖
├── infra/               # 基础设施
│   ├── Dockerfile       # 容器镜像
│   ├── docker-compose.yml
│   └── deploy.sh        # 部署脚本
├── docs/                # 完整文档
│   ├── API_DOCUMENTATION.md      # API 参考
│   ├── BACKEND_README.md         # 后端详解
│   ├── LOGIN_SECURITY.md         # 安全机制
│   └── ...
├── scripts/             # 运维脚本
│   ├── encrypt_existing_accounts.py  # 数据加密迁移
│   ├── cleanup_email_cache.py        # 缓存清理
│   ├── run_smoke_tests.py            # 冒烟测试
│   └── security_scan.sh              # 安全扫描
├── data/                # 运行时数据（Git 忽略）
│   ├── outlook_manager.db   # SQLite 数据库
│   ├── logs/                # 日志文件
│   └── static/              # 前端构建产物
└── .env                 # 环境配置（需手动创建）
```

## 🚀 快速开始

### 环境要求

- Python 3.12+
- Node.js 18+
- SQLite 3

### 1. 克隆项目

```bash
git clone <repository-url>
cd outlooker
```

### 2. 配置环境变量

```bash
# 复制环境变量模板
cp .env.example .env

# 生成必需的密钥
python -c "import secrets; print('JWT_SECRET_KEY=' + secrets.token_urlsafe(32))" >> .env
python -c "import secrets; print('DATA_ENCRYPTION_KEY=' + secrets.token_urlsafe(32))" >> .env
python -c "import secrets; print('ADMIN_PASSWORD=' + secrets.token_urlsafe(16))" >> .env

# 编辑 .env 补充其他配置（CLIENT_ID 等）
nano .env
```

### 3. 启动后端

```bash
cd backend
pip install -r requirements.txt
python -m app.mail_api web
# 后端将在 http://localhost:5001 启动
```

### 4. 启动前端（新终端）

```bash
cd frontend
npm install
npm run dev
# 前端将在 http://localhost:5173 启动
```

### 5. 访问应用

- **验证码工具**: http://localhost:5001/
- **管理后台**: http://localhost:5001/admin/login
- **API 文档**: http://localhost:5001/docs

## 🐳 Docker 部署

```bash
# 方式一：使用部署脚本
cd infra
chmod +x deploy.sh
./deploy.sh build
./deploy.sh start

# 方式二：直接使用 docker-compose
cd infra
docker-compose up -d
```

容器将在 http://localhost:5001 提供服务。

## 📚 完整文档

| 文档 | 说明 |
|------|------|
| [后端功能说明](docs/BACKEND_README.md) | 后端架构、数据库设计、核心功能 |
| [快速开始指南](docs/BACKEND_QUICKSTART.md) | 开发环境配置、常见任务 |
| [API 参考文档](docs/API_DOCUMENTATION.md) | 完整的 REST API 接口说明 |
| [登录安全机制](docs/LOGIN_SECURITY.md) | 频率限制、防爆破、审计日志 |
| [安全测试指南](docs/SECURITY_TESTING_GUIDE.md) | 安全改进验证步骤 |
| [依赖维护策略](docs/DEPENDENCY_MAINTENANCE.md) | 依赖升级和安全审计 |

## 🔧 开发命令

| 任务 | 命令 |
|------|------|
| 后端开发 | `cd backend && python -m app.mail_api web` |
| 前端开发 | `cd frontend && npm run dev` |
| 前端构建 | `cd frontend && npm run build` |
| 后端测试 | `cd backend && pytest` |
| 前端测试 | `cd frontend && npm run test` |
| 代码检查 | `cd backend && ruff check .` / `cd frontend && npm run lint` |
| 安全扫描 | `./scripts/security_scan.sh` |

## 🔒 安全特性

Outlooker 实现了多层安全防护：

### 认证与授权
- ✅ JWT Token 认证（默认 24 小时有效期）
- ✅ 管理员密码 bcrypt 哈希存储
- ✅ Legacy Token 默认禁用（可选开启）

### 数据保护
- ✅ 敏感数据（密码、Refresh Token）使用 Fernet 对称加密
- ✅ 环境变量管理密钥，支持密钥轮换
- ✅ 数据库自动迁移和版本管理

### 防护机制
- ✅ 登录频率限制（5 分钟内最多 5 次失败）
- ✅ 失败锁定（锁定 15 分钟）
- ✅ 审计日志（所有登录尝试记录）
- ✅ CORS 白名单控制

### 日志审计
- ✅ 登录审计日志：`data/logs/login_audit.log`
- ✅ 敏感信息脱敏
- ✅ 查看工具：`python scripts/view_login_audit.py`

## 🛠️ 运维脚本

| 脚本 | 用途 |
|------|------|
| `scripts/encrypt_existing_accounts.py` | 迁移旧账户数据到加密存储 |
| `scripts/cleanup_email_cache.py` | 清理过期邮件缓存 |
| `scripts/test_security_improvements.py` | 安全改进自动化验证 |
| `scripts/test_rate_limiting.py` | 频率限制功能测试 |
| `scripts/view_login_audit.py` | 查看登录审计日志统计 |
| `scripts/run_smoke_tests.py` | 部署后冒烟测试 |
| `scripts/security_scan.sh` | 依赖安全扫描 |

## 📊 主要功能

### 1. 邮件查看与验证码提取

- 支持多邮箱账户管理
- 分页、搜索、文件夹切换
- 自动识别 4-6 位验证码
- 一次性加载完整邮件正文
- 支持 HTML 和纯文本邮件

### 2. 账户管理

- 批量导入/导出（支持文本格式）
- 账户标签分类和过滤
- 分页和模糊搜索
- 敏感信息加密存储
- 脱敏预览（密码、Token）

### 3. 系统配置

- 邮件获取数量配置
- 缓存管理（一键刷新）
- 运行指标监控
- 配置文件和数据库双重持久化

### 4. 管理后台

- JWT 安全登录
- 账户 CRUD 操作
- 标签管理界面
- 系统配置面板
- 缓存和指标监控

## 🧪 测试

```bash
# 后端测试
cd backend
pytest                    # 运行所有测试
pytest -v                 # 详细输出
pytest --cov=app          # 覆盖率报告

# 前端测试
cd frontend
npm run test              # 运行测试
npm run test:watch        # 监听模式
```

## 🐛 故障排查

### 后端无法启动

```bash
# 检查环境变量
cat .env | grep -E "JWT_SECRET_KEY|DATA_ENCRYPTION_KEY|CLIENT_ID"

# 查看日志
tail -f data/logs/login_audit.log
```

### 数据加密问题

```bash
# 验证密钥配置
python -c "import os; print('KEY:', 'SET' if os.getenv('DATA_ENCRYPTION_KEY') else 'NOT SET')"

# 重新运行加密迁移
python scripts/encrypt_existing_accounts.py
```

### 前端无法连接后端

```bash
# 检查后端是否运行
curl http://localhost:5001/docs

# 检查 CORS 配置
grep ALLOWED_ORIGINS .env
```

## 📝 环境变量说明

```bash
# 必需配置
JWT_SECRET_KEY=<随机生成的密钥>        # JWT 签名密钥
DATA_ENCRYPTION_KEY=<随机生成的密钥>   # 数据加密密钥
CLIENT_ID=<Microsoft OAuth2 客户端ID>  # Azure AD 应用ID

# 管理员配置
ADMIN_USERNAME=admin                    # 管理员用户名
ADMIN_PASSWORD=<强密码>                # 管理员密码

# 可选配置
APP_ENV=development                     # 环境标识（development/production）
ALLOWED_ORIGINS=http://localhost:5173   # CORS 白名单（逗号分隔）
ENABLE_LEGACY_ADMIN_TOKEN=false         # 是否启用旧版Token
DEFAULT_EMAIL_LIMIT=10                  # 默认邮件获取数量
```

## 🤝 贡献指南

欢迎贡献代码！请遵循以下流程：

1. Fork 项目
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交改动 (`git commit -m 'Add some AmazingFeature'`)
4. 推送分支 (`git push origin feature/AmazingFeature`)
5. 提交 Pull Request

### 代码规范

- 后端：遵循 PEP 8，使用 `ruff` 进行代码检查
- 前端：遵循 ESLint 配置
- 提交信息：清晰描述改动内容

## 📄 许可证

本项目采用 MIT 许可证 - 详见 [LICENSE](LICENSE) 文件

## 📮 联系方式

- 问题反馈：[GitHub Issues](../../issues)
- 功能建议：[GitHub Discussions](../../discussions)

---

<div align="center">

**使用 ❤️ 和 ☕ 构建**

[📖 文档](docs/) · [🐛 报告问题](../../issues) · [✨ 功能请求](../../discussions)

</div>
