# Outlook Fixture 测试策略

## 1. 目标

对以下高脆弱逻辑做离线回归：

- Graph 响应映射
- 协议 HTML/JS 解析
- 协议任务状态机
- 渠道与租约逻辑

## 2. 目录

- `tests/backend/fixtures/outlook_protocol`
- `tests/backend/fixtures/outlook_graph`
- `tests/backend/fixtures/outlook_tasks`
- `tests/backend/fixtures/channeling`

## 3. 命名建议

- `protocol_phaseX_*.html`
- `graph_*.json`
- `task_*.json`
- `channel_*.json`

## 4. 最低要求

- 新增协议解析逻辑必须配 fixture
- 新增 Graph 映射逻辑必须配 mock/fixture
- 状态机变更必须配状态流测试

