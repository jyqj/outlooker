# 前端开发指南

## 1. 当前前端结构

核心目录：

```text
frontend/src/
├── components/
│   ├── ui/
│   └── outlook/
├── pages/
│   ├── dashboard/
│   ├── outlook/
│   ├── tags/
│   └── settings/
├── hooks/
├── lib/
│   ├── api/
│   ├── constants.ts
│   ├── hooks.ts
│   └── queryKeys.ts
├── i18n/
└── types/
```

## 2. 页面分层

- 旧工作台：`AdminDashboardPage`、`TagsPage`、`SettingsPage`、`AuditPage`
- 新工作台：
  - `OutlookAccountsPage`
  - `OutlookAccountDetailPage`
  - `OutlookTasksPage`
  - `AuxEmailPoolPage`
  - `ChannelConsolePage`

## 3. 数据流

- API client：`frontend/src/lib/api/*`
- Query keys：`frontend/src/lib/queryKeys.ts`
- 通用 hooks：`frontend/src/lib/hooks.ts`

新 Outlook 工作台主要通过以下接口文件访问后端：

- `outlook-accounts-api.ts`
- 默认 `api` client

## 4. 运行方式

```bash
cd frontend
npm install
npm run dev
```

开发服务器默认监听 `5173`，并通过 Vite 代理 `/api` 到 `5001`。

## 5. 测试

```bash
# 类型检查
npm run typecheck

# 单测
npm run test

# E2E
npm exec -- playwright test
```

## 6. 约束

- 新页面优先走 hooks，不要直接在页面里堆 axios
- 管理端受保护接口必须走 `api` client，由它统一补 Bearer token
- 新导航文案优先写入 `i18n`
- 工作台页面优先保证可操作和可维护，不追求装饰性 UI

