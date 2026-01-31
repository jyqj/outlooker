[← 返回文档目录](./README.md)

# Outlooker 依赖维护与安全扫描策略

本文档指导如何安全地升级依赖并执行例行安全审计，确保 **Outlooker** 在长期维护中保持可预测、可验证和安全的状态。

## 1. 后端（Python）升级流程

1. **创建隔离环境**
   ```bash
   cd backend
   python -m venv .venv && source .venv/bin/activate
   pip install -r requirements.txt
   ```
2. **检查可升级项**
   ```bash
   pip list --outdated
   ```
3. **分批升级关键依赖**
   - 优先 `fastapi`, `uvicorn`, `pydantic`, `pydantic-settings`
   - 每升级 1~2 个核心依赖后，运行：
     ```bash
     pytest --maxfail=1
     ```
4. **运行安全审计**
   ```bash
   pip-audit
   ```
5. **记录变更**
   - 在 PR/提交说明中写明升级范围与验证结果
   - 若遇到兼容性问题，记录在 [依赖维护](./maintenance.md) 供后续参考

## 2. 前端（Node.js）升级流程

1. **安装依赖**
   ```bash
   cd frontend
   npm install
   ```
2. **查看过期包**
   ```bash
   npm outdated
   ```
3. **分批升级**
   - 优先升级 `react`, `react-router-dom`, `@tanstack/react-query`, `vite`
   - 升级后运行：
     ```bash
     npm run lint
     npm run test
     npm run build
     ```
4. **安全审计**
   ```bash
   npm audit --audit-level=high
   ```

## 3. 统一安全扫描脚本

项目根目录提供 `scripts/security/security_scan.sh`，按顺序执行：

```bash
chmod +x scripts/security/security_scan.sh
scripts/security/security_scan.sh
```

- 需要提前安装 `pip-audit`
- 若发现高危依赖，先记录在 issue 中，再决定升级或替换方案

## 4. 重点关注的安全依赖

### 后端关键依赖

以下依赖直接影响系统安全，需要密切关注漏洞公告：

- **cryptography**: 用于敏感数据加密，关注 CVE 公告
- **python-jose[cryptography]**: JWT token 生成和验证
- **passlib[bcrypt]**: 密码哈希
- **fastapi**: Web 框架，关注 CORS、认证相关更新
- **pydantic**: 数据验证，关注注入攻击防护
- **httpx / requests**: HTTP 客户端，关注 SSRF 防护

**检查命令**：
```bash
cd backend
pip list --outdated | grep -E "cryptography|jose|passlib|fastapi|pydantic|httpx|requests"
pip-audit --desc  # 详细安全报告
```

### 前端关键依赖

- **axios**: HTTP 客户端，关注 XSS 和请求劫持防护
- **react / react-dom**: 核心框架，关注 XSS 和注入漏洞
- **react-router-dom**: 路由，关注导航安全
- **@tanstack/react-query**: 数据获取，关注缓存污染

**检查命令**：
```bash
cd frontend
npm outdated axios react react-dom react-router-dom @tanstack/react-query
npm audit --audit-level=moderate
```

## 5. 代码质量检查命令

### 后端 Lint 检查

使用 ruff 进行静态分析（配置见 `backend/pyproject.toml`）：

```bash
cd backend
pip install ruff
ruff check .           # 检查代码问题
ruff check . --fix     # 自动修复
ruff format .          # 代码格式化
```

### 前端 Lint 检查

```bash
cd frontend
npm run lint           # ESLint 检查
npm run lint -- --fix  # 自动修复
```

## 6. CI 校验

仓库提供 `.github/workflows/ci.yml`，在 Push/PR 时自动执行：

- 后端：`ruff check` + `pytest`
- 前端：`npm run lint` + `npm run test`

本地升级依赖后，请先跑通同等流程再提交。

## 7. 建议的例行任务

| 频率 | 任务 |
|------|------|
| 每周 | 运行 `scripts/security/security_scan.sh`，同步三方漏洞公告 |
| 每月 | 分析 `pip list --outdated` 与 `npm outdated`，规划升级批次 |
| 每季度 | 编写依赖升级报告，评估技术债与潜在弃用 API；运行 `ruff` 和 `npm run lint` 检查代码质量 |

## 8. 升级检查清单

在升级依赖前，使用以下清单确保安全：

- [ ] 已创建独立的测试分支
- [ ] 已备份 `requirements.txt` 和 `package.json`
- [ ] 已阅读升级包的 CHANGELOG
- [ ] 已在本地运行完整测试套件（`pytest` + `npm run test`）
- [ ] 已手动验证关键功能（登录、导入、邮件查看）
- [ ] 已更新 README 或文档中的版本要求说明

严格执行以上流程，可以让依赖升级与安全闭环都具备"可重复、可回溯"的特性。 
