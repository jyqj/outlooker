# 缓存性能说明

当前缓存主要分两类：

- 账户缓存：`AccountCacheService`
- 邮件缓存：`email_cache` / `email_cache_meta`

## 1. 当前目标

- 降低重复读取数据库和 IMAP 的成本
- 让旧邮箱池与新 Outlook 工作台共享稳定的账户读取入口

## 2. 建议观察项

- `/api/system/metrics`
- `email_manager.cache_hit_rate`
- `email_manager.email_cache.total_messages`

## 3. 常见操作

```bash
curl -X POST http://localhost:5001/api/system/cache/refresh \
  -H "Authorization: Bearer <token>"
```

