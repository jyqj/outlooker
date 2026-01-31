[← 返回文档目录](./README.md)

# 前端开发指南

本文档提供 Outlooker 前端开发的详细指南，包括架构设计、组件使用、最佳实践等。

## 目录

- [技术栈](#技术栈)
- [项目结构](#项目结构)
- [开发环境](#开发环境)
- [组件库](#组件库)
- [状态管理](#状态管理)
- [API 集成](#api-集成)
- [样式规范](#样式规范)
- [测试](#测试)
- [最佳实践](#最佳实践)

---

## 技术栈

| 技术 | 版本（参考 package.json） | 用途 |
|------|--------------------------|------|
| React | 19.x | UI 框架 |
| TypeScript | 5.7+ | 类型系统 |
| Vite | 7.x | 构建工具 |
| Tailwind CSS | 4.1.x | 样式框架 |
| TanStack Query | 5.x | 服务端状态管理 |
| React Router | 7.x | 客户端路由 |
| Axios | 1.13.x | HTTP 客户端 |
| i18next | 24.x | 国际化 |
| Playwright | 1.49.x | E2E 测试 |
| Vitest | 4.x | 单元测试框架 |
| Testing Library | 16.x | 组件测试 |

---

## 项目结构

下方结构与当前 `frontend/src` 目录保持同步，便于按图索骥：

```
frontend/
├── src/
│   ├── components/                  # 业务及复合组件
│   │   ├── ui/                      # UI 基础组件（Shadcn-like）
│   │   │   ├── Alert.tsx
│   │   │   ├── Badge.tsx
│   │   │   ├── Button.tsx
│   │   │   ├── Card.tsx
│   │   │   ├── ConfirmDialog.tsx
│   │   │   ├── Dialog.tsx
│   │   │   ├── Input.tsx
│   │   │   ├── LoadingSpinner.tsx
│   │   │   ├── Skeleton.tsx
│   │   │   └── index.ts
│   │   ├── EmailViewModal.tsx       # 邮件查看模态框
│   │   ├── EmailMetadata.tsx        # 邮件元数据组件
│   │   ├── ImportModal.tsx          # 批量导入模态框
│   │   ├── TagManageModal.tsx       # 标签管理模态框
│   │   ├── PickAccountModal.tsx     # 取号模态框
│   │   ├── VerificationCodeCard.tsx # 验证码卡片
│   │   ├── VerificationResultCard.tsx
│   │   ├── VerificationSearchForm.tsx
│   │   ├── LanguageSwitcher.tsx     # 语言切换组件
│   │   ├── ThemeProvider.tsx        # 主题提供者
│   │   ├── ThemeToggle.tsx          # 主题切换
│   │   ├── ErrorBoundary.tsx        # 错误边界
│   │   ├── StatusCard.tsx           # 状态卡片
│   │   └── Toast.tsx                # 全局提示容器
│   ├── pages/                       # 页面组件
│   │   ├── dashboard/               # 管理后台子模块
│   │   │   ├── components/          # 仪表板组件
│   │   │   │   ├── AccountsTable.tsx
│   │   │   │   ├── AccountTableRow.tsx
│   │   │   │   ├── BatchTagModal.tsx
│   │   │   │   ├── DashboardHeader.tsx
│   │   │   │   ├── DashboardToolbar.tsx
│   │   │   │   ├── Pagination.tsx
│   │   │   │   ├── SystemOverview.tsx
│   │   │   │   └── index.ts
│   │   │   └── hooks/               # 仪表板 Hooks
│   │   │       ├── useAccountSelection.ts
│   │   │       ├── useBatchOperations.ts
│   │   │       ├── useDashboardModals.ts
│   │   │       ├── usePagination.ts
│   │   │       └── index.ts
│   │   ├── AdminDashboardPage.tsx   # 管理后台主页
│   │   ├── AdminLoginPage.tsx       # 管理后台登录页
│   │   ├── VerificationPage.tsx     # 验证码工具页
│   │   ├── TagsPage.tsx             # 标签管理页
│   │   └── NotFoundPage.tsx         # 404 页面
│   ├── hooks/                       # 全局自定义 Hooks
│   │   ├── useVerification.ts
│   │   └── index.ts
│   ├── lib/                         # 工具库
│   │   ├── api.ts                   # Axios API 客户端
│   │   ├── constants.ts             # 常量配置
│   │   ├── download.ts              # 下载工具
│   │   ├── error.ts                 # 错误处理
│   │   ├── hooks.ts                 # 通用 Hooks（useDebounce 等）
│   │   ├── queryKeys.ts             # React Query Key 管理
│   │   ├── sanitize.ts              # HTML 清洗
│   │   ├── tagValidation.ts         # 标签验证
│   │   ├── toast.ts                 # Toast 调用封装
│   │   └── utils.ts                 # 通用工具函数
│   ├── types/                       # TypeScript 类型定义
│   │   ├── api.ts                   # API 响应类型
│   │   ├── components.ts            # 组件 Props 类型
│   │   ├── models.ts                # 数据模型类型
│   │   └── index.ts
│   ├── i18n/                        # 国际化配置
│   │   ├── index.ts
│   │   └── locales/
│   │       ├── zh-CN.json           # 中文翻译
│   │       └── en.json              # 英文翻译
│   ├── assets/                      # 前端静态资源
│   │   └── react.svg
│   ├── App.tsx                      # 根组件
│   ├── App.css                      # 根组件样式
│   ├── main.tsx                     # 应用入口
│   └── index.css                    # 全局样式
├── e2e/                             # E2E 测试 (Playwright)
│   ├── login.spec.ts
│   └── verification.spec.ts
├── public/                          # 静态资源
│   └── favicon.svg                  # 网站图标
├── eslint.config.js                 # ESLint 配置（flat config）
├── vite.config.ts                   # Vite 配置（TypeScript）
├── tsconfig.json                    # TypeScript 配置
├── playwright.config.ts             # Playwright E2E 测试配置
├── index.html                       # Vite HTML 模板
├── package.json                     # 依赖配置
└── package-lock.json                # 锁定依赖版本
```

---

## 开发环境

### 安装依赖

```bash
cd frontend
npm install
```

### 启动开发服务器

```bash
npm run dev
```

访问 http://localhost:5173

### 构建生产版本

```bash
npm run build
```

构建产物位于项目根目录的 `data/static/` 目录（由 Vite `build.outDir = '../data/static'` 指定），后端会直接挂载并提供这些静态文件。

### 预览生产版本

```bash
npm run preview
```

### 代码检查

```bash
npm run lint
```

### 运行测试

```bash
npm run test          # 运行单元测试
npm run test:watch    # 监听模式
npm run test:e2e      # 运行 E2E 测试 (Playwright)
npm run test:e2e:ui   # E2E 测试 UI 模式
```

---

## 组件库

### UI 基础组件

所有 UI 组件位于 `src/components/ui/`，采用 Shadcn-like 风格设计。

#### Button

```jsx
import { Button } from '@/components/ui/Button';

<Button variant="default" size="md">
  点击我
</Button>
```

**Props**:
- `variant`: `default` | `outline` | `ghost` | `destructive`
- `size`: `sm` | `md` | `lg`
- `disabled`: boolean

#### Input

```jsx
import { Input } from '@/components/ui/Input';

<Input
  type="text"
  placeholder="请输入..."
  value={value}
  onChange={(e) => setValue(e.target.value)}
/>
```

#### Card

```jsx
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/Card';

<Card>
  <CardHeader>
    <CardTitle>标题</CardTitle>
  </CardHeader>
  <CardContent>
    内容
  </CardContent>
</Card>
```

#### Dialog

```jsx
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/Dialog';

<Dialog open={isOpen} onOpenChange={setIsOpen}>
  <DialogContent>
    <DialogHeader>
      <DialogTitle>对话框标题</DialogTitle>
    </DialogHeader>
    <div>对话框内容</div>
  </DialogContent>
</Dialog>
```

#### Badge

```jsx
import { Badge } from '@/components/ui/Badge';

<Badge variant="default">标签</Badge>
```

**Variants**: `default` | `secondary` | `outline` | `destructive`

---

## 状态管理

### TanStack Query (React Query) v5

用于管理服务端状态（API 数据）。

#### 基本用法

```jsx
import { useQuery } from '@tanstack/react-query';
import api from '@/lib/api';

function AccountList() {
  const { data, isLoading, error } = useQuery({
    queryKey: ['accounts', page, pageSize],
    queryFn: async ({ signal }) => {
      const response = await api.get('/api/accounts/paged', {
        params: { page, page_size: pageSize },
        signal, // 支持请求取消
      });
      return response.data;
    },
    placeholderData: (previousData) => previousData, // 保持上一次数据
  });

  if (isLoading) return <div>加载中...</div>;
  if (error) return <div>错误: {error.message}</div>;

  return <div>{/* 渲染数据 */}</div>;
}
```

#### 常用配置

- `queryKey`: 查询键（数组），用于缓存和去重
- `queryFn`: 查询函数，返回 Promise
- `placeholderData`: 保持上一次数据，优化用户体验
- `staleTime`: 数据过期时间（默认 0）
- `gcTime`: 缓存垃圾回收时间（默认 5 分钟）
- `refetchOnWindowFocus`: 窗口聚焦时重新获取（默认 true）

#### Mutation（修改数据）

```jsx
import { useMutation, useQueryClient } from '@tanstack/react-query';

function DeleteAccount() {
  const queryClient = useQueryClient();

  const mutation = useMutation({
    mutationFn: (email) => api.delete(`/api/accounts/${email}`),
    onSuccess: () => {
      // 刷新账户列表
      queryClient.invalidateQueries({ queryKey: ['accounts'] });
    },
  });

  return (
    <button onClick={() => mutation.mutate('user@example.com')}>
      删除
    </button>
  );
}
```

### 本地状态

使用 React Hooks 管理本地状态：

```jsx
import { useState, useEffect } from 'react';

function Component() {
  const [count, setCount] = useState(0);
  const [email, setEmail] = useState('');

  useEffect(() => {
    // 副作用
  }, [email]);

  return <div>{count}</div>;
}
```

---

## API 集成

### API 客户端

位于 `src/lib/api.ts`，基于 Axios 封装。

#### 特性

- ✅ 自动注入 JWT Token
- ✅ 401 自动跳转到登录页
- ✅ 统一错误处理
- ✅ 支持 AbortSignal 取消请求

#### 使用示例

```jsx
import api from '@/lib/api';

// GET 请求
const response = await api.get('/api/accounts/paged', {
  params: { page: 1, page_size: 10 },
  signal: abortSignal, // 可选
});

// POST 请求
const response = await api.post('/api/accounts', {
  email: 'user@example.com',
  password: 'password',
});

// DELETE 请求
await api.delete(`/api/accounts/${email}`);

// PUT 请求
await api.put(`/api/accounts/${email}`, {
  password: 'new_password',
});
```

#### 错误处理

```jsx
try {
  const response = await api.get('/api/accounts');
} catch (error) {
  if (error.response) {
    // 服务器返回错误
    console.error(error.response.data.message);
  } else if (error.request) {
    // 请求发送失败
    console.error('网络错误');
  } else {
    // 其他错误
    console.error(error.message);
  }
}
```

---

## 样式规范

### Tailwind CSS 使用

#### 透明度规范 (v2.3.0)

| 透明度 | 用途 | 示例 |
|--------|------|------|
| `/10` | 极浅背景 | 警告框、信息框 |
| `/20` | 浅背景 | 分页栏 |
| `/40` | 中等背景 | Header、图标背景 |
| `/60` | 明显背景 | 页面背景 |
| `/80` | 深背景 | 悬停状态、元信息 |

#### 颜色系统

```jsx
// 主题色
<div className="bg-primary text-primary-foreground">主题色</div>

// 背景色
<div className="bg-background">背景</div>
<div className="bg-muted">次要背景</div>

// 文字色
<div className="text-foreground">主文字</div>
<div className="text-muted-foreground">次要文字</div>

// 边框色
<div className="border border-border">边框</div>
```


#### 阴影系统

```jsx
<div className="shadow-sm">轻微阴影</div>
<div className="shadow-md">中等阴影</div>
<div className="shadow-lg">深阴影</div>
<div className="shadow-xl">超深阴影</div>
```

#### 暗色模式

使用 `dark:` 前缀：

```jsx
<div className="bg-white dark:bg-gray-950">
  <p className="text-gray-900 dark:text-gray-100">文字</p>
</div>
```

#### 响应式设计

```jsx
<div className="text-sm md:text-base lg:text-lg">
  响应式文字大小
</div>

<div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3">
  响应式网格
</div>
```

### cn 工具函数

用于合并类名：

```jsx
import { cn } from '@/lib/utils';

<div className={cn(
  'base-class',
  isActive && 'active-class',
  className // 外部传入的类名
)}>
  内容
</div>
```

---

## 测试

### 测试框架

- **Vitest**: 单元测试框架
- **Testing Library**: React 组件测试

### 运行测试

```bash
npm run test          # 运行单元测试
npm run test:watch    # 监听模式
npm run test:e2e      # 运行 E2E 测试 (Playwright)
npm run test:e2e:ui   # E2E 测试 UI 模式
```

### 测试示例

```jsx
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, it, expect, vi } from 'vitest';
import VerificationPage from '../VerificationPage';

describe('VerificationPage', () => {
  it('renders email input', () => {
    render(<VerificationPage />);
    expect(screen.getByLabelText(/邮箱地址/)).toBeInTheDocument();
  });

  it('fetches verification code on submit', async () => {
    const user = userEvent.setup();
    render(<VerificationPage />);

    await user.type(screen.getByLabelText(/邮箱地址/), 'test@example.com');
    await user.click(screen.getByRole('button', { name: /获取/ }));

    await waitFor(() => {
      expect(screen.getByText(/验证码/)).toBeInTheDocument();
    });
  });
});
```

### 测试最佳实践

1. **使用语义化查询**: 优先使用 `getByRole`, `getByLabelText`
2. **模拟 API**: 使用 `vi.mock` 模拟 API 调用
3. **等待异步**: 使用 `waitFor` 等待异步操作
4. **用户交互**: 使用 `userEvent` 模拟用户操作
5. **清理**: 每个测试后自动清理 DOM

---

## 最佳实践

### 1. 组件设计

- ✅ 单一职责原则：每个组件只做一件事
- ✅ 组件复用：提取可复用的 UI 组件
- ✅ Props 验证：使用 PropTypes 或 TypeScript
- ✅ 默认值：为 Props 提供合理的默认值

### 2. 性能优化

- ✅ 懒加载：大型组件使用 `React.lazy`
- ✅ 防抖：搜索框使用 `useDebounce`
- ✅ 骨架屏：加载状态使用 Skeleton
- ✅ 请求取消：使用 AbortSignal 取消过期请求
- ✅ 缓存：使用 TanStack Query 缓存数据

### 3. 代码规范

- ✅ ESLint：遵循 ESLint 规则
- ✅ 命名规范：组件用 PascalCase，函数用 camelCase
- ✅ 文件组织：相关文件放在同一目录
- ✅ Props 类型位置：局部 Props 就近定义；跨组件复用的 variant/union 类型集中到 `src/types/components.ts`
- ✅ 注释：复杂逻辑添加注释

### 4. 错误处理

- ✅ 边界情况：处理空数据、错误状态
- ✅ 用户反馈：显示清晰的错误信息
- ✅ 加载状态：显示加载动画
- ✅ 空状态：显示友好的空状态提示

### 5. 可访问性

- ✅ 语义化 HTML：使用正确的 HTML 标签
- ✅ ARIA 属性：为交互元素添加 ARIA 属性
- ✅ 键盘导航：支持键盘操作
- ✅ 对比度：确保文字和背景有足够对比度

### 6. Git 提交

- ✅ 提交前测试：确保所有测试通过
- ✅ 提交前检查：运行 `npm run lint`
- ✅ 提交信息：使用清晰的提交信息
- ✅ 小步提交：每次提交只做一件事

---

## 常见问题

### Q: 如何添加新页面？

1. 在 `src/pages/` 创建新组件
2. 在 `App.jsx` 添加路由
3. 添加对应的测试文件

### Q: 如何添加新的 UI 组件？

1. 在 `src/components/ui/` 创建组件
2. 遵循 Shadcn-like 风格
3. 使用 Tailwind CSS
4. 添加 PropTypes 或 TypeScript 类型

### Q: 如何调试 API 请求？

1. 打开浏览器开发者工具
2. 查看 Network 标签
3. 检查请求和响应
4. 使用 `console.log` 打印数据

### Q: 如何处理 401 错误？

API 客户端会自动处理 401 错误，跳转到登录页。

### Q: 如何更新依赖？

```bash
npm update          # 更新所有依赖
npm outdated        # 查看过期依赖
```

---

## 相关文档

- [README.md](../README.md) - 项目总览
- [CHANGELOG.md](../CHANGELOG.md) - 版本历史
- [API 参考](./api-reference.md) - API 文档
- UI 设计系统：计划拆分为独立文档，目前请参考组件实现与 Tailwind 配置

---

**最后更新**: 2026-01-28 (v2.4.0)
