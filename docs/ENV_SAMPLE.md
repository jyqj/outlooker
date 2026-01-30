## 环境变量示例

将以下内容保存为项目根目录的 `.env`（或 `backend/.env`），敏感值请自行替换：

```
APP_ENV=development

# 管理员（仅初始化用，生产请改为强口令）
ADMIN_USERNAME=admin
ADMIN_PASSWORD=change-me-strong-password

# 安全密钥
JWT_SECRET_KEY=change-me-jwt-secret-please
DATA_ENCRYPTION_KEY=change-me-encryption-key

# OAuth / IMAP
CLIENT_ID=your-azure-client-id
TOKEN_URL=https://login.microsoftonline.com/consumers/oauth2/v2.0/token
IMAP_SERVER=outlook.live.com
IMAP_PORT=993
INBOX_FOLDER_NAME=INBOX
JUNK_FOLDER_NAME=Junk

# 邮件缓存
EMAIL_CACHE_TTL_SECONDS=15

# Token 生命周期
ACCESS_TOKEN_EXPIRE_MINUTES=1440
REFRESH_TOKEN_EXPIRE_DAYS=7

# 刷新令牌 Cookie（默认开启，生产请使用 HTTPS）
ADMIN_REFRESH_COOKIE=true
ADMIN_REFRESH_COOKIE_NAME=outlooker_rtk
ADMIN_REFRESH_COOKIE_SECURE=false
ADMIN_REFRESH_COOKIE_PATH=/

# 公共接口调用口令（生产必填）
PUBLIC_API_TOKEN=dev-public-token-change-me

# CORS
ALLOWED_ORIGINS=http://localhost:5173,http://localhost:5001

# 路径
DATABASE_PATH=data/outlook_manager.db
LOGS_DIR=data/logs
STATIC_DIR=data/static
```
