# 测试指南

## 1. 后端

推荐使用 `Python 3.12` 运行后端测试：

```bash
cd backend
pytest
```

如果本机默认 `python3` 不是 3.12，可使用：

```bash
cd backend
uv run --python 3.12 --with-requirements requirements-dev.txt pytest
```

## 2. 前端

```bash
npm --prefix frontend run typecheck
npm --prefix frontend run test
```

## 3. Playwright

先安装浏览器：

```bash
npm --prefix frontend exec playwright install
```

运行 E2E：

```bash
cd frontend
npm exec -- playwright test
```

## 4. 冒烟

后端启动后执行：

```bash
python3 scripts/run_smoke_tests.py
```

当前 smoke 已覆盖：

- `/api/accounts`
- `/api/system/metrics`
- `/api/outlook/accounts`
- `/api/outlook/accounts/batch-refresh`
- `/api/outlook/tasks`

## 5. Fixture

协议与 Graph 相关测试资源在：

- `tests/backend/fixtures/outlook_protocol`
- `tests/backend/fixtures/outlook_graph`
- `tests/backend/fixtures/outlook_tasks`
- `tests/backend/fixtures/channeling`

## 6. 当前已验证结果

当前仓库已经验证通过：

- 后端新增模块测试
- 受影响旧接口测试
- 前端 `typecheck`
- 前端 Vitest
- 新工作台多浏览器 E2E

