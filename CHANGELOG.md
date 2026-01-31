# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [2.5.0] - 2026-01-31

### 🏗️ 代码架构改进

#### 统一异常处理
- ✅ 新增 `handle_exceptions` 装饰器 (`backend/app/core/decorators.py`)
- ✅ 重构 18 个 API 端点使用统一异常处理
- ✅ 减少每个端点约 6-8 行重复代码
- ✅ 代码更简洁、错误处理更一致

#### 向后兼容层
- ✅ 添加 `backend/app/jwt_auth.py` 兼容旧导入路径
- ✅ 添加 `backend/app/rate_limiter.py` 兼容旧导入路径
- ✅ 确保平滑升级，无需修改外部依赖代码

### 📊 性能监控

#### API 指标收集
- ✅ 新增 `MetricsMiddleware` 中间件自动收集请求指标
- ✅ 记录请求次数、响应时间（平均/最小/最大）、错误率
- ✅ 慢请求自动警告（超过 1 秒）
- ✅ 线程安全，支持高并发

#### 监控端点
- ✅ `GET /api/system/metrics` - 获取 API 性能指标
- ✅ `POST /api/system/metrics/reset` - 重置统计数据
- ✅ `GET /api/system/metrics/system` - 系统运行指标

### 🔒 安全改进

#### 启动时验证
- ✅ 新增 `validate_environment()` 函数
- ✅ 生产环境自动检查安全配置
- ✅ 记录配置警告到日志

#### 配置管理
- ✅ 移除前端 `api.ts` 中的硬编码 Token
- ✅ 统一使用 `constants.ts` 中的常量定义

### 🧪 测试改进

#### 测试导入路径修复
- ✅ 修复 6 个测试文件的旧导入路径
- ✅ 共修复 11 处导入语句
- ✅ 测试覆盖率保持 70%

#### 测试工具
- ✅ 新增 `tests/backend/utils.py` 测试辅助模块
- ✅ 提供 `create_test_account()` 等工厂函数
- ✅ 提供 `MockIMAPClient` 模拟类

### 📁 新增文件

```
backend/app/
├── jwt_auth.py              # 向后兼容导入
├── rate_limiter.py          # 向后兼容导入
└── core/
    ├── decorators.py        # 异常处理装饰器
    ├── metrics.py           # API 指标收集
    ├── middleware.py        # 监控中间件
    └── startup.py           # 启动验证

tests/backend/
└── utils.py                 # 测试辅助工具
```

### 📊 测试结果

- 后端测试：215/215 通过 (100%)
- 覆盖率：70%
- TypeScript 类型检查：通过
- ESLint 检查：通过

---

## [2.4.0] - 2026-01-28

### 🚀 新功能

#### E2E 测试 (FUTURE-001)
- ✅ 引入 Playwright E2E 测试框架
- ✅ 添加登录流程测试 (`e2e/login.spec.ts`)
  - 表单显示验证
  - 空凭据错误处理
  - 无效凭据错误处理
  - 成功登录重定向
  - 安全性测试（频率限制）
- ✅ 添加验证码获取流程测试 (`e2e/verification.spec.ts`)
  - 表单显示验证
  - 邮箱验证
  - 加载状态测试
  - 响应式布局测试
- ✅ 支持多浏览器测试 (Chromium, Firefox, WebKit, Mobile)
- ✅ 新增 `npm run test:e2e` 和 `npm run test:e2e:ui` 命令

#### 错误监控 APM (FUTURE-002)
- ✅ 集成 Sentry Browser SDK (前端)
  - 自动错误捕获
  - 性能监控 (Browser Tracing)
  - 会话回放 (Session Replay)
- ✅ 集成 Sentry Python SDK (后端)
  - FastAPI 自动集成
  - 性能追踪
- ✅ 通过环境变量配置 (`SENTRY_DSN`, `VITE_SENTRY_DSN`)
- ✅ 开发/生产环境自动调整采样率

#### 国际化 i18n (FUTURE-003)
- ✅ 引入 react-i18next 国际化框架
- ✅ 支持中文 (zh-CN) 和英文 (en) 双语
- ✅ 完整的翻译文件覆盖所有 UI 文案
- ✅ 语言切换组件 (`LanguageSwitcher`)
- ✅ 自动检测浏览器语言
- ✅ 语言偏好持久化 (localStorage)

### 📊 性能优化决策 (PERF-001-C)
- ✅ 完成 IMAP 连接池化调研结论
- ✅ 决策：**暂不实现连接池**，采用方案 C（保持现状 + 缓存策略优化）
- ✅ 原因：当前流量较低，现有客户端复用已足够，实现复杂度高
- ✅ 更新 `docs/PERF_IMAP_POOLING.md` 文档

### 🏗️ 代码架构重构
- ✅ 认证模块重构：`backend/app/auth/` 目录
  - `jwt.py` - JWT 认证
  - `security.py` - 数据加密
  - `oauth.py` - OAuth2 集成
  - `refresh_token.py` - 刷新令牌管理
- ✅ 核心功能模块化：`backend/app/core/` 目录
  - `exceptions.py` - 统一异常处理
  - `messages.py` - 消息常量
  - `rate_limiter.py` - 频率限制
- ✅ 工具函数整理：`backend/app/utils/` 目录
- ✅ 脚本目录重组：
  - `scripts/benchmarks/` - 性能基准测试
  - `scripts/maintenance/` - 维护脚本
  - `scripts/security/` - 安全脚本

### 📦 依赖更新

**前端新增依赖:**
- `@sentry/react`: ^8.45.0
- `@playwright/test`: ^1.49.0
- `i18next`: ^24.2.2
- `react-i18next`: ^15.4.1

**后端新增依赖:**
- `sentry-sdk[fastapi]`: ==2.19.2

### 📁 新增文件

```
frontend/
├── playwright.config.ts         # Playwright 配置
├── e2e/
│   ├── login.spec.ts            # 登录 E2E 测试
│   └── verification.spec.ts     # 验证码 E2E 测试
└── src/
    ├── i18n/
    │   ├── index.ts             # i18n 配置入口
    │   └── locales/
    │       ├── zh-CN.json       # 中文翻译
    │       └── en.json          # 英文翻译
    └── components/
        └── LanguageSwitcher.tsx # 语言切换组件

backend/app/
├── auth/                        # 认证模块（重构）
│   ├── jwt.py
│   ├── security.py
│   ├── oauth.py
│   └── refresh_token.py
├── core/                        # 核心功能（重构）
│   ├── exceptions.py
│   ├── messages.py
│   └── rate_limiter.py
└── utils/                       # 工具函数（新增）
    ├── pagination.py
    ├── request_utils.py
    └── validation.py

scripts/
├── benchmarks/                  # 性能基准测试（重组）
├── maintenance/                 # 维护脚本（重组）
└── security/                    # 安全脚本（重组）
```

### 🔧 配置更新

**新增环境变量 (.env.example):**
- `SENTRY_DSN`: 后端 Sentry DSN
- `VITE_SENTRY_DSN`: 前端 Sentry DSN

**新增 npm 脚本:**
- `test:e2e`: 运行 Playwright E2E 测试
- `test:e2e:ui`: 运行 Playwright UI 模式

---

## [2.3.0] - 2025-11-20

### 🎨 前端全面优化和功能增强

#### UI/UX 改进

**透明度设计统一**
- 优化所有组件的透明度值，提升视觉层次和可读性
- 页面背景: `bg-muted/30` → `bg-muted/60` (更明显的层次感)
- Dialog 背景: `bg-black/50` → `bg-black/70` + `backdrop-blur-md` (更强的焦点)
- 卡片阴影: `shadow-sm` → `shadow-md` (更立体的视觉效果)
- 表格悬停: `hover:bg-muted/50` → `hover:bg-muted/80` (更明显的交互反馈)
- 导航栏: 添加 `shadow-md` + `backdrop-blur-sm` (更清晰的分层)

**EmailViewModal 全面改进**
- ✅ 添加明确的加载状态（Loader2 旋转动画 + "正在获取邮件..."提示文字）
- ✅ 优化验证码显示：
  - 大字号显示 (`text-5xl md:text-6xl`)
  - 渐变背景 (`bg-gradient-to-br from-blue-50 to-indigo-50`)
  - 一键复制功能 + 复制成功提示
  - 图标使用 emoji (🔐) 避免加载问题
- ✅ 改进邮件元信息布局：
  - 使用纯色背景 (`bg-gray-50 dark:bg-gray-900`)
  - 图标放在带背景的小容器中
  - 发件人和时间分行显示更清晰
  - 时间格式更详细 (年月日时分秒)
- ✅ 所有内容区域使用纯色不透明背景：
  - Dialog 容器: `bg-white dark:bg-gray-950`
  - Header: `bg-gray-100 dark:bg-gray-900`
  - 邮件正文: `bg-gray-50 dark:bg-gray-900`
- ✅ 完善空状态和错误状态显示
- ✅ 支持 HTML 和纯文本邮件渲染

**VerificationPage 重构**
- ✅ 移除高级功能：
  - 删除 Refresh Token 输入框
  - 删除"高级选项"切换按钮
  - 删除邮件数量选择器
- ✅ 统一视觉风格与管理端一致：
  - 使用 Card、Button、Input 组件
  - 页面背景: `bg-muted/60`
  - 统一的文字颜色和字体大小
  - 完美支持暗色模式
- ✅ 简化为核心功能：
  - 输入邮箱地址
  - 获取最新验证码按钮 (大字号 + 加粗 + 边框设计)
  - 显示最新 1 封邮件的验证码
  - 刷新按钮 (在验证码卡片右上角)
- ✅ 改进状态反馈：
  - 加载状态: Loader2 旋转动画 + 提示文字
  - 错误状态: AlertCircle 图标 + 清晰的错误信息
  - 成功状态: 验证码卡片 + 一键复制
- ✅ 扁平化按钮设计 (`border-2` 替代阴影)
- ✅ 响应式布局优化

#### 分页功能增强 (AdminDashboardPage)

- ✅ 添加每页显示数量选择器：
  - 选项: 10/20/50/100 条/页
  - 默认值: 10 条/页
  - 切换时自动重置到第 1 页
- ✅ 添加智能页码选择器：
  - 始终显示: 第 1 页、最后一页、当前页
  - 当前页前后各显示 1-2 个页码
  - 中间省略的部分用 "..." 表示
  - 示例: `1 ... 5 6 [7] 8 9 ... 20`
  - 页码按钮可点击直接跳转
- ✅ 添加跳转到指定页功能：
  - 文本输入框 (移除数字输入框的上下箭头)
  - 输入验证: 只接受数字，验证范围 (1 到最大页数)
  - 按回车键或点击"跳转"按钮执行跳转
  - 输入无效页码时显示错误提示
- ✅ 添加总记录数统计显示 ("共 X 条记录")
- ✅ 改进移动端响应式布局：
  - 移动端: 简化布局，垂直排列
  - 桌面端: 完整功能，水平排列
- ✅ 所有分页控件样式与设计系统保持一致

#### 其他改进

- ✅ 更换网站图标为邮件图标 (📧 SVG)
- ✅ 更新页面标题为 "Outlooker - 邮箱验证码管理"
- ✅ HTML lang 属性从 "en" 改为 "zh-CN"
- ✅ 完善暗色模式支持
- ✅ 优化空状态显示 (图标放大、透明度调整)
- ✅ 统一警告框和信息提示框样式

### 🔧 代码质量优化

**React 代码改进**
- ✅ 修复 React Hooks 使用问题 (TagManageModal 使用 component key 模式重置状态)
- ✅ 移除所有调试 console.log 语句
- ✅ 更新 React Query 到 v5 API:
  - `keepPreviousData` → `placeholderData: (previousData) => previousData`
  - 添加 AbortSignal 支持请求取消
- ✅ 更新 ESLint 配置支持测试文件 (添加 vitest globals)

**代码组织**
- ✅ 统一组件导入顺序
- ✅ 优化组件结构和可读性
- ✅ 改进错误处理逻辑

### 🧪 测试

**前端测试更新**
- ✅ 更新 VerificationPage 测试以匹配简化功能：
  - 移除 Refresh Token 相关测试
  - 更新错误消息断言
  - 移除 `api.post` mock (不再使用)
- ✅ 更新 AdminDashboardPage 测试以匹配新分页 UI：
  - 更新分页文本断言 ("第 1 页" → "共 25 条记录")
- ✅ 所有测试保持 100% 通过率 (23/23)

### 📊 统计数据

| 指标 | v2.2.1 | v2.3.0 | 变化 |
|------|--------|--------|------|
| 前端测试通过率 | 100% | 100% | - |
| 前端测试数量 | 23 | 23 | - |
| 代码质量 | 良好 | 优秀 | ↑ |
| UI 一致性 | 中等 | 优秀 | ↑↑ |
| 用户体验 | 良好 | 优秀 | ↑↑ |

### 🔄 Breaking Changes

**VerificationPage API 变更**
- ⚠️ 前端不再使用 `POST /api/temp-messages` 接口
- ⚠️ 统一使用 `GET /api/messages` (数据库账户模式)
- ⚠️ 移除了临时账户模式的前端支持 (API 仍然可用)

**注意**: 此变更仅影响前端，后端 API 保持向后兼容

---

## [2.2.1] - 2025-01-20

### 🎯 代码质量改进

#### 重构
- **删除冗余代码**: 移除了730行的冗余 `backend/app/services.py` 文件
  - 所有功能已迁移到模块化的 `backend/app/services/` 目录
  - 提升了代码可维护性和清晰度
  - 确保单一数据源原则(Single Source of Truth)

#### 测试覆盖提升
- **后端测试**: 从63个测试增加到95个测试 (+51%)
  - 新增 `test_jwt_auth.py`: JWT认证和密码哈希测试(15个测试)
  - 新增 `test_database.py`: 数据库CRUD操作测试(9个测试)
  - 新增 `test_migrations.py`: 数据库迁移系统测试(8个测试)
  - 测试通过率: 100% (95 passed, 1 skipped)

- **前端测试**: 通过率从56%提升到100%
  - 创建缺失的 `Alert.jsx` UI组件
  - 修复了ImportModal和AdminDashboardPage的测试依赖问题
  - 测试通过率: 100% (23 passed)

#### 测试覆盖的关键领域
- ✅ JWT认证和授权机制
- ✅ 密码哈希和验证(bcrypt)
- ✅ 数据库CRUD操作
- ✅ 数据库迁移系统
- ✅ 账户导入和合并逻辑
- ✅ 系统配置管理
- ✅ 数据加密和解密(Fernet)
- ✅ React组件渲染和交互

### 📊 统计数据

| 指标 | 改进前 | 改进后 | 提升 |
|------|--------|--------|------|
| 后端测试数量 | 63 | 95 | +51% |
| 前端测试通过率 | 56% | 100% | +44% |
| 总测试数量 | 79 | 118 | +49% |
| 代码冗余 | 730行重复 | 0 | -100% |

### 🔧 技术改进
- 改进了测试隔离性(使用临时数据库和fixture)
- 增强了测试的可读性和可维护性
- 统一了测试命名规范和组织结构

---

## [2.2.0] - 2025-01-15

### Added
- 完整的JWT认证系统
- 数据加密存储(Fernet)
- 登录频率限制和审计日志
- React 19前端重构
- Docker容器化部署支持

### Changed
- 升级到Python 3.12
- 升级到React 19
- 重构服务层为模块化架构

### Security
- 实现bcrypt密码哈希
- 添加CORS白名单控制
- 敏感数据加密存储

---

## [2.1.0] - 2024-12-01

### Added
- 批量账户导入/导出功能
- 账户标签管理
- 系统配置面板
- 缓存管理功能

### Improved
- 优化IMAP连接复用
- 改进邮件缓存机制
- 提升前端性能

---

## [2.0.0] - 2024-11-01

### Added
- 全新的管理后台界面
- 验证码自动提取功能
- 多账户支持
- 邮件分页和搜索

### Changed
- 重构为前后端分离架构
- 采用FastAPI替代Flask
- 使用React替代传统模板引擎

---

## [1.0.0] - 2024-10-01

### Added
- 初始版本发布
- 基础邮件查看功能
- 简单的账户管理
- SQLite数据存储

