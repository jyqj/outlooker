[← 返回文档目录](./README.md)

# SQLite 邮件缓存性能压测（PERF-002）

## 结论

- 在当前实现“每个邮箱最多缓存 100 封邮件”的约束下，即使 `email_cache` 总记录数达到 **100 万**，核心查询（按邮箱分页拉取/按 message_id 查单封/统计状态）仍保持在 **~0.01ms–0.11ms** 级别（本机压测）。
- 额外索引对读取收益不明显，反而会增加写入/导入成本；建议保持现状，优先依赖 `UNIQUE(email, folder, message_id)` 产生的索引。
- 现阶段 **无需迁移** 其他存储。若未来放宽“每邮箱 100 封”或引入跨邮箱范围查询，再重新评估（可考虑引入 `uid_int` 列+索引以避免 `ORDER BY CAST(...)` 的表达式排序）。

## 如何复现

```bash
python3 scripts/benchmark_email_cache.py
python3 scripts/benchmark_email_cache.py --sizes 100000 500000 1000000 --sample 200
python3 scripts/benchmark_email_cache.py --with-extra-indexes
```

默认会在 `/tmp/outlooker-bench/` 生成对应规模的 SQLite 文件。

## 压测设置

- SQLite: 3.43.2
- Python: 3.9.6
- 规模: 100k / 500k / 1,000k 行
- 分布: `per_account=100`（模拟实现中的上限），账户数分别为 1k / 5k / 10k
- 抽样: 200 个邮箱，每个查询执行 200 次（n=200），统计 avg/median/p95

## 压测结果（不额外建索引）

| 规模 | 写入耗时 | `get_cached_messages` avg/p95 | `get_cached_email` avg/p95 | `get_cache_state` avg/p95 | `get_cache_meta` avg/p95 |
|---:|---:|---:|---:|---:|---:|
| 100k | 0.28s | 0.087ms / 0.094ms | 0.007ms / 0.007ms | 0.013ms / 0.014ms | 0.004ms / 0.004ms |
| 500k | 1.50s | 0.087ms / 0.096ms | 0.006ms / 0.006ms | 0.012ms / 0.013ms | 0.004ms / 0.004ms |
| 1,000k | 2.98s | 0.087ms / 0.094ms | 0.008ms / 0.009ms | 0.014ms / 0.015ms | 0.004ms / 0.004ms |

## 额外索引对比

脚本的 `--with-extra-indexes` 会创建：

- `idx_email_cache_email_folder_id_desc(email, folder, id DESC)`
- `idx_email_cache_email_folder_received_id_desc(email, folder, received_date DESC, id DESC)`

结论：读取延迟无明显收益，但写入耗时显著上升（例如 100 万行写入从 ~3s 增加到 ~5.7s），因此不建议默认启用。

## 建议

1. **保持 `per_account=100` 上限**（当前实现已做）。这是使性能稳定的关键。
2. 如未来需要提升单邮箱缓存上限（例如 500/1000+），建议：
   - 引入 `uid_int`（INTEGER）列保存 IMAP UID，避免 `ORDER BY CAST(message_id AS INTEGER)`；
   - 为 `(email, folder, uid_int DESC)` 建索引，并改写查询使用该列排序。
3. 保持定期清理策略（已有 `scripts/maintenance/cleanup_email_cache.py`），避免长期增长造成磁盘膨胀。

