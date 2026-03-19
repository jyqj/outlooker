# 敏感日志规范

以下内容不允许明文写日志：

- 密码
- access token / refresh token
- client secret
- OTP / OTC / 验证码
- PPFT / sFT / canary / apiCanary
- proofId
- Cookie / Authorization

## 工具

统一使用：

- [redaction.py](/Users/jin/Desktop/outlooker/backend/app/utils/redaction.py)

核心函数：

- `mask_secret`
- `mask_email`
- `mask_code`
- `redact_log_data`

## 原则

- 协议日志默认脱敏
- 审计明细默认脱敏
- 不直接打印原始 HTML / 表单体 / 完整响应正文

