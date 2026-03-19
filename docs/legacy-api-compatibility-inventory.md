# 旧接口兼容清单

以下接口仍视为兼容接口，重构期间不可随意改路径或响应主结构：

## 1. 账户池

- `/api/accounts`
- `/api/accounts/paged`
- `/api/accounts/pick`
- `/api/accounts/batch-delete`
- `/api/accounts/batch-tags`
- `/api/accounts/health-check`

## 2. 标签

- `/api/accounts/tags`
- `/api/accounts/tags/stats`
- `/api/accounts/{email}/tags`
- `/api/tags`

## 3. 验证码

- `/api/messages`
- `/api/temp-messages`
- `/api/test-email`

## 4. 当前兼容原则

- 新能力统一走 `/api/outlook/*`
- 旧 `/api/accounts/pick` 已兼容渠道模型，但保留旧调用方式
- 旧标签接口不能被渠道概念替代

