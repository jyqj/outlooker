# Outlooker 前端

基于 React 19 + Vite + Tailwind CSS 构建的现代化单页应用，提供邮件查看、账户管理和系统配置界面。

## 开发

```bash
cd frontend
npm install          # 首次
npm run dev          # http://localhost:5173
```

- `.env` 中的 `VITE_API_BASE` 可覆盖默认代理，空字符串表示与当前域同源。
- 管理后台、验证码页面、导入/导出、标签管理均在此项目维护。

## 构建

```bash
npm run build
```

- 输出目录：`../data/static/`
- FastAPI 会托管 `/static` 与 `/assets`，因此构建后无需额外配置。

## 代码风格

- 使用 React + React Router + React Query。
- 样式基于 Tailwind CSS（`cn` 与 `tailwind-merge`）。
- API 请求统一通过 `src/lib/api.js`（axios 实例），已内置 401 自动跳转。

## 可选脚本

```bash
npm run lint
npm run preview
```

> 构建产物已加入 `.gitignore`，请在部署或提交前手动运行 `npm run build`。
