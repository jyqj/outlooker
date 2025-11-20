# Outlooker 前端

基于 React 19 + Vite + Tailwind CSS 4 + TanStack Query v5 构建的现代化单页应用，提供邮件查看、账户管理和系统配置界面。

## 技术栈

- **React 19**: 最新的 React 版本，使用 Hooks
- **Vite**: 快速的构建工具和开发服务器
- **Tailwind CSS 4**: 原子化 CSS 框架
- **TanStack Query v5**: 强大的服务端状态管理
- **React Router v7**: 客户端路由
- **Axios**: HTTP 客户端
- **Vitest**: 单元测试框架
- **Testing Library**: React 组件测试

## 开发

```bash
cd frontend
npm install          # 首次安装依赖
npm run dev          # 启动开发服务器 (http://localhost:5173)
```

- `.env` 中的 `VITE_API_BASE` 可覆盖默认代理，空字符串表示与当前域同源。
- 管理后台、验证码页面、导入/导出、标签管理均在此项目维护。

## 架构特性

### 1. UI 组件系统
采用 Shadcn-like 风格的原子化组件设计，位于 `src/components/ui/`：
- **基础组件**: Button, Input, Badge, Card, Skeleton, Alert
- **卡片组件**: Card, CardHeader, CardContent, CardTitle, CardDescription
- **复合组件**: Dialog (统一模态框交互)
- **样式管理**: 基于 Tailwind CSS 4，使用 CSS 变量管理主题，支持 `cn` 工具函数合并类名。

### 2. 设计系统 (v2.3.0)

**透明度规范**:
- `/10`: 极浅背景（警告框、信息框）
- `/20`: 浅背景（分页栏）
- `/40`: 中等背景（Header、图标背景）
- `/60`: 明显背景（页面背景）
- `/80`: 深背景（悬停状态、元信息）

**颜色系统**:
- 主题色: `primary` (蓝色)
- 背景色: `background`, `muted`
- 文字色: `foreground`, `muted-foreground`
- 边框色: `border`
- 完美支持暗色模式 (`dark:` 前缀)

**阴影系统**:
- `shadow-sm`: 轻微阴影
- `shadow-md`: 中等阴影（卡片、按钮）
- `shadow-lg`: 深阴影（Dialog、验证码区域）
- `shadow-xl`: 超深阴影（悬停效果）

### 3. 性能优化
- **Code Splitting**: 大型模态框（导入、邮件查看）使用 `React.lazy` + `Suspense` 懒加载。
- **Debounce**: 搜索框集成 `useDebounce` Hook，减少 API 请求频率。
- **Skeleton Loading**: 列表加载状态使用骨架屏优化视觉体验。
- **请求取消**: 使用 AbortSignal 支持请求取消，避免竞态条件。

### 4. 数据管理
- 使用 **TanStack Query (React Query) v5** 管理服务端状态（缓存、去重、自动刷新）。
- API 请求统一封装在 `src/lib/api.js`，内置 Auth Token 注入和 401 自动跳转。
- 使用 `placeholderData` 保持上一次数据，优化用户体验。

## 构建

```bash
npm run build
```

- 输出目录：`../data/static/`
- FastAPI 会托管 `/static` 与 `/assets`，因此构建后无需额外配置。

## 代码风格

- 使用 React 19 + Hooks。
- 样式基于 Tailwind CSS 4。
- 组件尽量保持纯展示，逻辑抽离到 Hooks。

## 可选脚本

```bash
npm run lint         # ESLint 代码检查
npm run test         # Vitest 单元测试 (23 个测试)
npm run test:watch   # 监听模式运行测试
npm run preview      # 预览构建产物
```

> 构建产物已加入 `.gitignore`，请在部署或提交前手动运行 `npm run build`。

## 主要页面

### 1. VerificationPage (`/`)
简化的验证码获取界面：
- 输入邮箱地址（数据库账户）
- 获取最新 1 封邮件
- 智能提取验证码
- 一键复制功能
- v2.3.0 已移除临时账户模式

### 2. AdminDashboardPage (`/admin`)
管理后台主界面：
- 账户列表（分页、搜索）
- 增强的分页功能（v2.3.0）
- 批量导入/导出
- 标签管理
- 邮件查看

### 3. AdminLoginPage (`/admin/login`)
管理员登录界面：
- JWT 认证
- 频率限制
- 审计日志

## v2.3.0 更新

### UI/UX 改进
- ✅ 统一透明度设计，提升视觉层次
- ✅ EmailViewModal 全面改进（加载状态、验证码显示、布局优化）
- ✅ VerificationPage 重构（移除高级功能，统一视觉风格）
- ✅ 分页功能增强（页码选择器、跳转功能、每页数量选择）
- ✅ 更换网站图标为邮件图标
- ✅ 完善暗色模式支持

### 代码质量
- ✅ 修复 React Hooks 使用问题
- ✅ 更新 React Query 到 v5 API
- ✅ 添加 AbortSignal 支持
- ✅ 移除调试代码
- ✅ 更新 ESLint 配置

### 测试
- ✅ 23 个测试全部通过
- ✅ 更新测试以匹配新功能
