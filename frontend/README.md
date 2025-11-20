# Outlooker 前端

基于 React 19 + Vite + Tailwind CSS 4 构建的现代化单页应用，提供邮件查看、账户管理和系统配置界面。

## 开发

```bash
cd frontend
npm install          # 首次
npm run dev          # http://localhost:5173
```

- `.env` 中的 `VITE_API_BASE` 可覆盖默认代理，空字符串表示与当前域同源。
- 管理后台、验证码页面、导入/导出、标签管理均在此项目维护。

## 架构特性

### 1. UI 组件系统
采用 Shadcn-like 风格的原子化组件设计，位于 `src/components/ui/`：
- **基础组件**: Button, Input, Badge, Card, Skeleton
- **复合组件**: Dialog (统一模态框交互)
- **样式管理**: 基于 Tailwind CSS 4，使用 CSS 变量管理主题，支持 `cn` 工具函数合并类名。

### 2. 性能优化
- **Code Splitting**: 大型模态框（导入、邮件查看）使用 `React.lazy` + `Suspense` 懒加载。
- **Debounce**: 搜索框集成 `useDebounce` Hook，减少 API 请求频率。
- **Skeleton Loading**: 列表加载状态使用骨架屏优化视觉体验。

### 3. 数据管理
- 使用 **TanStack Query (React Query)** 管理服务端状态（缓存、去重、自动刷新）。
- API 请求统一封装在 `src/lib/api.js`，内置 Auth Token 注入和 401 自动跳转。

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
npm run lint         # 代码检查
npm run test         # 单元测试
npm run preview      # 预览构建产物
```

> 构建产物已加入 `.gitignore`，请在部署或提交前手动运行 `npm run build`。
