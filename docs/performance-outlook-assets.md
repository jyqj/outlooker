# Outlook 资产读模型性能与安全边界

## 背景

旧的 `/api/outlook/accounts` 列表链路先读取账户页，然后针对每个账户分别查询：

1. 最新 active OAuth Token；
2. 账户能力位。

最后再单独执行总数查询。因此一页 `N` 个账户的数据库任务预算为：

```text
1 + 2N + 1
```

默认上限 100 时，单次请求最多产生 202 个线程池任务、SQLite 连接和查询边界。Token 查询还会解密 access token 与 refresh token，并将这些不被前端使用的凭据放入 JSON 响应。

## 当前读模型

`OutlookAssetReadMixin` 将账户、能力位与最新 active Token 元数据投影到一个 JOIN 查询中：

- 列表：一个线程池任务、一个 SQLite 连接、同一只读快照内完成 `COUNT + page projection`；
- 详情：一个线程池任务内聚合账户视图、资料缓存、验证方式快照和最近操作；
- Token：只选择状态、到期时间、scope 与凭据存在性，不读取或解密 Token 正文；
- 分页：服务端和 Pydantic 请求模型都限制单页最多 200 条；
- 索引：按资产排序、状态筛选、类型筛选和最新 Token 查找建立工作负载索引。

公开 Token 视图允许以下字段：

```text
id, oauth_config_id, email, expires_at, scopes_granted,
status, last_error, created_at, updated_at,
has_access_token, has_refresh_token
```

`access_token` 和 `refresh_token` 不属于管理 API 的响应契约。

## 基准

仓库提供合成基准：

```bash
python scripts/benchmarks/benchmark_outlook_asset_views.py \
  --accounts 10000 \
  --page-size 100 \
  --iterations 20
```

脚本对比：

- legacy：模拟列表查询、每账户两次独立连接查询和总数查询；
- projection：单连接中的总数与 JOIN 投影。

一次本地合成运行（1000 个账户、页面 100、5 次采样）得到：

```text
legacy median:     43.235 ms, 202 DB tasks
projection median:  0.421 ms,   1 DB task
median speedup:   102.75x
```

该结果用于验证开销模型与检测回退，不等同于生产 SLA。真实收益取决于磁盘、CPU、SQLite cache、并发和部署环境。

## 回归检查

相关测试验证：

- 列表和详情各只进入一次 `_run_in_thread`；
- 最新 Token 选择正确；
- 响应中不存在 Token 正文；
- 筛选、总数、分页上界与资源限制生效；
- 工作负载索引完成创建；
- 批量刷新会去重邮箱、限制并发并保持结果顺序。
