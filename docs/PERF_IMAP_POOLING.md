# IMAP 连接复用/连接池化调研（PERF-001）

## 背景与现状

### 现状 1：服务层已有“客户端复用”

`EmailManager` 会按邮箱维度缓存 `IMAPEmailClient` 实例，并在同一邮箱 + refresh_token 未变化时复用客户端对象（降低重复初始化与 token 刷新开销）。

### 现状 2：IMAP 连接仍是“按需创建/用完即关”

`IMAPEmailClient` 的邮件拉取逻辑通过 `_imap_connection(...)` 以“上下文管理器”方式创建 IMAP 连接并在操作结束后关闭：

- ✅ 优点：实现简单、资源可控、避免长连接失效导致的异常堆积
- ⚠️ 代价：每次请求都会付出连接建立/认证/SELECT folder 的成本（尤其在高频调用或高并发时）

因此 PERF-001 的核心问题不是“有没有复用 client 对象”，而是 **是否要复用底层 IMAP 连接（socket/session）**。

## 目标

1. 给出可复现的基准测试方法与指标口径
2. 明确连接复用/连接池化的候选方案与取舍
3. 用数据判断是否值得进入实现阶段

## 基准测试方法

使用脚本 `scripts/benchmark_imap.py` 采集同一邮箱在两种模式下的延迟分布：

- `reuse-client`：复用同一个 `IMAPEmailClient`
- `new-client`：每次新建 `IMAPEmailClient`

示例：

```bash
python3 scripts/benchmark_imap.py --email user@example.com --refresh-token "M.C123..." --iterations 10 --mode reuse-client
python3 scripts/benchmark_imap.py --email user@example.com --refresh-token "M.C123..." --iterations 10 --mode new-client
```

建议跑法（更便于粘贴到文档/避免污染默认 DB）：

```bash
python3 scripts/benchmark_imap.py \
  --email user@example.com \
  --refresh-token "M.C123..." \
  --database-path data/benchmark_imap.db \
  --warmup 1 \
  --iterations 20 \
  --mode reuse-client \
  --redact \
  --json
```

### 指标口径（建议）

- 成功率：`success / iterations`
- 延迟：avg / median / p95（单次调用 `get_messages_with_content` 总耗时）
- QPS：脚本会输出 `total` 与 `qps`，也可用 `success / total_time_seconds` 手算
- 额外维度（可选）：`top` 参数不同（例如 1/5/20）下的延迟变化

> 注意：该脚本会写入本地 SQLite 缓存（与服务端行为一致），因此结果反映“真实链路”而非纯 IMAP。

### 结果记录模板（PERF-001-C 回填）

| mode | top | warmup | iterations | success | avg(ms) | median(ms) | p95(ms) | qps | 备注 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| reuse-client |  |  |  |  |  |  |  |  |  |
| new-client |  |  |  |  |  |  |  |  |  |

## 候选方案与取舍

### 方案 A：短 TTL 连接复用（推荐优先评估）

思路：在 `IMAPEmailClient` 内部维护一个“可复用连接”，并通过锁保证同一连接不会被并发使用。

- ✅ 优点：实现成本低；对现有调用方改动小；显著减少握手/认证开销
- ⚠️ 风险：连接可能被服务端断开；需要健康检查与自动重连；需要处理 folder select 的一致性
- 适用：同一邮箱在短时间内被频繁查询（例如验证码轮询）

### 方案 B：连接池（并发场景）

思路：每个邮箱/文件夹维护一个连接池（如 `asyncio.Queue`），每次请求借出一个连接，完成后归还，池内连接定期保活/清理。

- ✅ 优点：吞吐更高；并发更友好；可显式限制最大连接数
- ⚠️ 成本：实现复杂；需要严格的连接生命周期管理；imaplib 的线程/协程安全性需要额外约束
- 适用：同一邮箱存在并发拉取需求，且连接建立成本成为主要瓶颈

### 方案 C：不池化，仅做并发限制 + 缓存策略优化（低成本兜底）

思路：保持“按需连接”，但通过：

- 每邮箱 `asyncio.Semaphore` 限制并发拉取
- 更激进/更一致的缓存 TTL 策略（减少强制刷新）

来避免过多连接与频繁拉取。

- ✅ 优点：风险低、实现简单
- ⚠️ 缺点：对高频轮询的延迟改善有限

## 决策建议

1. 先跑 PERF-001-C 的数据采集（reuse-client vs new-client）确认是否存在明显的“client 初始化/鉴权”开销。
2. 若延迟主要由 IMAP 连接建立主导（且业务确实需要高频轮询/高并发），优先做 **方案 A**；
3. 只有在方案 A 不能满足吞吐或并发时，再进入 **方案 B（连接池）**。

---

## 最终结论（2026-01-28）

### 决策：暂不实现 IMAP 连接池，采用方案 C

#### 决策依据

1. **流量现状**：系统主要用于验证码获取场景，属于低频、偶发请求；当前未观察到因 IMAP 连接建立导致的性能瓶颈。

2. **现有优化已足够**：`EmailManager` 已实现 `IMAPEmailClient` 实例级别复用，避免了重复的 token 刷新和客户端初始化开销。

3. **投入产出比**：
   - 方案 A（短 TTL 连接复用）需处理连接健康检查、自动重连、folder select 一致性等问题
   - 方案 B（连接池）实现复杂度更高，需要处理 imaplib 线程安全、连接生命周期管理等
   - 当前业务场景下，这些投入难以带来显著的用户体验提升

4. **缓存策略已优化**：邮件缓存机制（SQLite）已减少大量不必要的 IMAP 请求

#### 采纳的优化措施（方案 C）

- ✅ 保持"按需连接"模式
- ✅ 继续复用 `IMAPEmailClient` 实例
- ✅ 维持现有邮件缓存策略
- ❌ 不引入连接池化

#### 重新评估条件

如果未来出现以下情况，应重新评估连接池化：

1. 并发请求量显著增加（如支持多用户同时查询）
2. 用户反馈邮件加载延迟明显
3. 监控数据显示 IMAP 连接建立耗时成为主要瓶颈（占比 > 50%）

#### 参考数据

由于系统处于低流量状态，正式基准数据采集意义有限。未来可按需使用 `scripts/benchmark_imap.py` 采集数据：

```bash
# 采集建议命令
python3 scripts/benchmark_imap.py \
  --email <your-email> \
  --refresh-token "<your-token>" \
  --database-path data/benchmark_imap.db \
  --warmup 2 \
  --iterations 20 \
  --mode reuse-client \
  --redact \
  --json
```
