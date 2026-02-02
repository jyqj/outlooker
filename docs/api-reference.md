[← 返回文档目录](./README.md)

# Outlooker API 文档

<div align="center">

**完整的 REST API 参考文档**

[![API Version](https://img.shields.io/badge/API%20Version-2.4.0-blue.svg)](.)
[![OpenAPI](https://img.shields.io/badge/OpenAPI-3.0-green.svg)](.)

</div>

---

## 目录

- [概述](#概述)
- [认证说明](#认证说明)
- [API 接口](#api-接口)
  - [页面路由](#页面路由)
  - [管理员认证](#管理员认证)
  - [邮件查看](#邮件查看)
  - [账户管理](#账户管理)
  - [标签管理](#标签管理)
  - [系统配置](#系统配置)
- [数据模型](#数据模型)
- [错误处理](#错误处理)
- [示例代码](#示例代码)

---

## 概述

**Outlooker** 提供了一套完整的 RESTful API，用于管理 Microsoft Outlook 邮箱账户、查看邮件和提取验证码。所有 API 遵循 REST 规范，使用 JSON 格式交换数据。

### 基础信息

| 项目 | 说明 |
|------|------|
| **基础 URL** | `http://localhost:5001` |
| **API 版本** | 2.4.0 |
| **协议** | HTTP/HTTPS |
| **数据格式** | JSON |
| **字符编码** | UTF-8 |

### 技术栈

- **后端框架**: FastAPI (Python 3.12)
- **数据库**: SQLite 3
- **认证方式**: JWT Token + Microsoft OAuth2
- **API 规范**: OpenAPI 3.0

### 交互式文档

开发环境下，你可以通过以下地址访问交互式 API 文档：

- **Swagger UI**: http://localhost:5001/docs
- **ReDoc**: http://localhost:5001/redoc

这些页面支持直接测试 API 接口，查看请求/响应示例。

---

## 认证说明

### JWT 认证流程

1. **获取 Token**

使用管理员用户名和密码登录，获取 JWT token：

```bash
curl -X POST "http://localhost:5001/api/admin/login" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "admin",
    "password": "<your-admin-password>"
  }'
```

> 提示：`<your-admin-password>` 必须与你在 `ADMIN_PASSWORD` 中配置的值一致；若在开发环境未设置密码，可在后端启动日志中查看系统随机生成的一次性密码。

响应：
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 86400
}
```

2. **使用 Token**

在后续请求的 `Authorization` header 中使用 token：

```bash
Authorization: Bearer {access_token}
```

3. **Token 有效期**

- 默认有效期：24 小时（86400 秒）
- Token 过期后需要重新登录

### 默认管理员账户

- **用户名**: 由 `ADMIN_USERNAME` 指定，默认值为 `admin`
- **密码**: 必须通过 `ADMIN_PASSWORD` 显式配置；如果在开发环境未设置，系统会在启动日志中生成并打印一次性随机密码

### 环境变量配置

```bash
# 管理员用户名
ADMIN_USERNAME=admin

# 管理员密码（支持明文或 bcrypt 哈希）
ADMIN_PASSWORD=<strong-password>
# 未设置 ADMIN_PASSWORD（仅限开发环境）时，系统会随机生成一次性密码并输出到日志

# JWT 密钥（生产环境必须设置）
JWT_SECRET_KEY=your-secret-key-change-this-in-production-please
```

---

## API 接口

### 端点分类速览

> 说明：本表用于快速判断某个端点的 **调用方 / 用途 / 是否属于调试接口**。详细字段请继续查看后续章节。

| Endpoint | Method | 认证 | 调用方 | 用途 | 备注 |
| --- | --- | --- | --- | --- | --- |
| `/` | GET | - | 浏览器 | 前端页面（验证码获取） | 静态资源入口 |
| `/admin` | GET | - | 浏览器 | 前端页面（管理后台） | 需先登录 |
| `/api/admin/login` | POST | - | 管理后台 | 管理员登录换取 `access_token` | 返回 `AdminLoginResponse` |
| `/api/admin/refresh` | POST | Bearer/Cookie | 管理后台 | 刷新 `access_token` | 依赖 HttpOnly Cookie（推荐） |
| `/api/admin/logout` | POST | Bearer/Cookie | 管理后台 | 登出并清理 refresh cookie | - |
| `/api/accounts/paged` | GET | Bearer | 管理后台 | 分页拉取账户列表 | 前端主要使用 |
| `/api/accounts` | GET/POST | Bearer | 管理后台/内部 | 获取全部/创建单账户 | 前端一般用分页/导入 |
| `/api/accounts/{email}` | GET/PUT/DELETE | Bearer | 管理后台/内部 | 单账户读写删 | 批量场景用批量接口 |
| `/api/accounts/tags` | GET | Bearer | 管理后台 | 拉取标签总表与映射 | - |
| `/api/accounts/{email}/tags` | GET/POST | Bearer | 管理后台 | 获取/更新单账户标签 | - |
| `/api/accounts/batch-delete` | POST | Bearer | 管理后台 | 批量删除账户 | - |
| `/api/accounts/batch-tags` | POST | Bearer | 管理后台 | 批量标签操作 | - |
| `/api/import` | POST | Bearer | 管理后台 | 批量导入账户 | - |
| `/api/parse-import-text` | POST | Bearer | 管理后台 | 导入前文本解析预览 | - |
| `/api/export` | GET | Bearer | 管理后台 | 导出账户 | - |
| `/api/system/config` | GET/POST | Bearer | 管理后台 | 读取/更新系统配置 | 运行时以 DB 为准 |
| `/api/system/metrics` | GET | Bearer | 管理后台/运维 | 获取系统指标 | - |
| `/api/system/cache/refresh` | POST | Bearer | 管理后台/运维 | 刷新账户缓存并清空邮件缓存 | - |
| `/api/messages` | GET | `X-Public-Token` | 验证码页面/外部 | 获取指定邮箱邮件列表 | 支持分页/搜索/刷新 |
| `/api/public/account-unused` | GET | `X-Public-Token` | 验证码页面/外部 | 获取一个未使用账户 | 自动接码流程 |
| `/api/public/account/{email}/otp` | GET | `X-Public-Token` | 验证码页面/外部 | 获取最新验证码 | 仅返回 code |
| `/api/public/account/{email}/used` | POST | `X-Public-Token` | 验证码页面/外部 | 标记账户已用 | 自动接码流程 |
| `/api/public/account/{email}` | DELETE | `X-Public-Token` | 外部/运维 | 删除账户（含标签与缓存） | 前端未使用 |
| `/api/temp-messages` | POST | `X-Public-Token` | 外部/运维 | 临时使用 refresh_token 拉取邮件 | `debug/internal` |
| `/api/test-email` | POST | `X-Public-Token` | 运维 | 测试 IMAP 拉取链路 | `debug/internal` |
| `/api/email/{email}/{message_id}` | DELETE | Bearer | 管理后台 | 删除本地缓存邮件 | 不保证删远端 |
| `/api/email/{email}/{message_id}/read` | POST | Bearer | 内部 | 标记缓存邮件为已读 | `deprecated/internal` |
| `/api/health/*` | GET | - | 运维/监控 | 健康检查 | K8s/探针 |

### 页面路由

#### 1. 主页面

**端点**: `GET /`

**描述**: 返回简化版验证码获取页面 (VerificationPage)

**认证**: 无需认证

**功能** (v2.3.0 简化版):
- 输入邮箱地址（必须是已配置的数据库账户）
- 自动获取最新 1 封邮件
- 智能提取 4-6 位验证码（大字号显示）
- 一键复制验证码到剪贴板
- 刷新按钮重新获取最新邮件
- 显示邮件主题、发件人、接收时间、正文
- 支持 HTML 和纯文本邮件渲染
- 明确的加载、错误、空状态提示

**设计理念**: 扁平化设计，统一视觉风格，移动端友好

**⚠️ 重要变更 (v2.3.0)**:
- 已移除临时账户模式（Refresh Token 输入）
- 仅支持数据库账户模式
- 固定显示最新 1 封邮件

**示例**:
```bash
curl http://localhost:5001/
```

---

#### 2. 管理后台页面

**端点**: `GET /admin`

**描述**: 返回管理后台页面 (AdminDashboardPage)

**认证**: 需要在页面中登录

**功能**:
- 账户列表查看和管理
- **增强的分页功能** (v2.3.0):
  - 每页显示数量选择（10/20/50/100 条）
  - 智能页码导航（当前页前后显示，中间省略号）
  - 快速跳转到指定页（输入框 + 验证）
  - 总记录数统计显示
  - 移动端响应式布局
- 批量导入/导出账户
- 标签管理
- 系统配置
- 邮件查看（完整正文 + 验证码提取）

**示例**:
```bash
curl http://localhost:5001/admin
```

---

### 管理员认证

#### 1. 管理员登录

**端点**: `POST /api/admin/login`

**描述**: 使用用户名和密码登录，返回 JWT token

**认证**: 无需认证

**请求体**:
```json
{
  "username": "admin",
  "password": "<your-admin-password>"
}
```

**响应**:
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 86400
}
```

**示例**:
```bash
curl -X POST "http://localhost:5001/api/admin/login" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "admin",
    "password": "<your-admin-password>"
  }'
```

---





#### 2. 验证管理令牌（已废弃）

**端点**: `POST /api/admin/verify`

**描述**: 验证旧的固定 token（向后兼容）

**认证**: 无需认证

**⚠️ 已废弃**: 建议使用 `/api/admin/login` 获取 JWT token

**请求体**:
```json
{
  "token": "<your-admin-token>"
}
```

**响应**:
```json
{
  "success": true,
  "message": "验证成功"
}
```

---

### 公共邮箱 & 自助接码接口

> 以下接口不需要管理员 JWT，但需要携带公共接口调用口令（`X-Public-Token`），可用于前端或第三方服务进行自助接码。
>
> - Header: `X-Public-Token: <PUBLIC_API_TOKEN>`
> - `PUBLIC_API_TOKEN` 来自后端环境变量（生产环境必须配置）

#### 1. 获取未使用的邮箱

**端点**: `GET /api/public/account-unused`

**描述**: 返回一个尚未使用过的邮箱账号（按创建时间最早排序）。

**认证**: 需要 `X-Public-Token`

**响应示例（成功）**:

```json
{
  "success": true,
  "message": "获取未使用邮箱成功",
  "data": {
    "email": "unused@example.com"
  }
}
```

**响应示例（无可用邮箱）**:

```json
{
  "success": false,
  "message": "暂无未使用的邮箱"
}
```

#### 2. 标记邮箱为已使用

**端点**: `POST /api/public/account/{email}/used`

**描述**: 将指定邮箱标记为“已使用”，并记录最后使用时间。

**认证**: 需要 `X-Public-Token`

**路径参数**:

- `email`: 要标记的邮箱地址

**响应示例**:

```json
{
  "success": true,
  "message": "账户已标记为已使用",
  "data": {
    "email": "user@example.com"
  }
}
```

#### 3. 删除指定邮箱

**端点**: `DELETE /api/public/account/{email}`

**描述**: 删除指定邮箱账户，同时删除其标签和缓存的邮件。

**认证**: 需要 `X-Public-Token`

**路径参数**:

- `email`: 要删除的邮箱地址

**响应示例**:

```json
{
  "success": true,
  "message": "账户已删除",
  "data": {
    "email": "user@example.com"
  }
}
```

#### 4. 获取指定邮箱最新验证码（接码）

**端点**: `GET /api/public/account/{email}/otp`

**描述**: 读取该邮箱最新一封邮件，使用服务端智能算法提取验证码，只返回验证码本身。

**认证**: 需要 `X-Public-Token`

**路径参数**:

- `email`: 要接码的邮箱地址（必须已在系统中配置）

**响应示例（成功）**:

```json
{
  "success": true,
  "message": "验证码解析成功",
  "data": {
    "code": "654321"
  }
}
```

**响应示例（无邮件或未识别到验证码）**:

```json
{
  "success": false,
  "message": "该邮箱暂无邮件"
}
```

或

```json
{
  "success": false,
  "message": "未自动识别到验证码"
}
```

---

### 邮件查看

#### 1. 获取邮件列表

**端点**: `GET /api/messages`

**描述**: 获取指定邮箱的最新邮件列表（包含完整正文），支持分页、模糊搜索和文件夹切换

**认证**: 需要 `X-Public-Token`（开发环境默认 `dev-public-token-change-me`，生产环境请在 `.env` 配置 `PUBLIC_API_TOKEN`）

**查询参数**:
- `email` *(必需)*: 邮箱地址
- `page` *(可选)*: 页码，默认 1
- `page_size` *(可选)*: 每页数量，默认 5，最大 50
- `folder` *(可选)*: 文件夹名称，默认 `INBOX`
- `search` *(可选)*: 模糊搜索关键字（匹配主题、发件人、正文预览）
- `refresh` *(可选)*: 是否强制刷新（`true/1` 时跳过本地缓存并触发 IMAP 拉取，同时更新缓存）

**响应**:
```json
{
  "success": true,
  "data": {
    "items": [
      {
        "id": "AAMkAGI1...",
        "subject": "测试邮件",
        "from": {
          "emailAddress": {
            "name": "Sender",
            "address": "sender@example.com"
          }
        },
        "receivedDateTime": "2024-11-19T10:30:00",
        "bodyPreview": "这是邮件预览...",
        "body": {
          "contentType": "html",
          "content": "<p>完整正文...</p>"
        }
      }
    ],
    "page": 1,
    "page_size": 5,
    "total": 12,
    "folder": "INBOX"
  }
}
```

**示例**:
```bash
# 分页 + 搜索
curl -H "X-Public-Token: <token>" "http://localhost:5001/api/messages?email=user@example.com&page=2&page_size=5&search=code"

# 切换文件夹
curl -H "X-Public-Token: <token>" "http://localhost:5001/api/messages?email=user@example.com&folder=Junk&page_size=10"

# 强制刷新（跳过缓存）
curl -H "X-Public-Token: <token>" "http://localhost:5001/api/messages?email=user@example.com&page_size=1&refresh=true"
```

服务端会将邮件写入 SQLite 缓存，默认在 `EMAIL_CACHE_TTL_SECONDS`（开发默认 15 秒）内重复请求会优先返回缓存数据。

---

#### 2. 临时账户获取邮件

**端点**: `POST /api/temp-messages`

**描述**: 无需预先配置账户，直接使用 refresh_token 获取邮件，参数与 `/api/messages` 一致

**认证**: 需要 `X-Public-Token`

**调用方 / 状态**:
- `debug/internal`：主要用于手工调试与第三方集成
- 管理后台前端当前不使用（仍保留以兼容外部调用）

**⚠️ 重要说明 (v2.3.0)**:
- 此接口主要供 **API 调用**使用
- **前端 VerificationPage 已不再使用此接口**（v2.3.0 起）
- 前端统一使用 `GET /api/messages`（数据库账户模式）
- API 仍然保持向后兼容，可供第三方集成使用

**请求体**:
```json
{
  "email": "user@example.com",
  "refresh_token": "M.C123...",
  "page": 1,
  "page_size": 5,
  "folder": "INBOX",
  "search": ""
}
```

**响应**: 与 `/api/messages` 相同（含分页信息）

**使用场景**:
- 临时查看邮件，不想保存账户配置
- 测试新账户是否可用
- 一次性查看邮件
- 第三方系统集成调用

---

#### 3. 测试邮件连接

**端点**: `POST /api/test-email`

**描述**: 测试指定邮箱账户的连接是否正常，并获取最新的 1 封邮件

**认证**: 需要 `X-Public-Token`

**调用方 / 状态**:
- `debug/internal`：用于运维/调试验证 refresh_token 与 IMAP 拉取链路
- 管理后台前端不使用；生产环境建议限制访问（仅对受信任的调用方开放）

**请求体**:
```json
{
  "email": "user@example.com",
  "refresh_token": "refresh_token_string"
}
```

**参数说明**:
- `email` (必需): 邮箱地址
- `refresh_token` (可选): 如果不提供则使用配置文件中的

**响应**:
```json
{
  "success": true,
  "data": {
    "message_id": "AAMkAGI1...",
    "subject": "测试邮件",
    "sender": "sender@example.com",
    "received_date": "2024-11-19T10:30:00",
    "body_preview": "这是邮件预览...",
    "body_content": "<html>完整邮件内容...</html>",
    "body_type": "html"
  },
  "message": "连接成功"
}
```

**示例**:
```bash
curl -X POST "http://localhost:5001/api/test-email" \
  -H "X-Public-Token: <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com"
  }'
```

**使用场景**:
- 验证账户配置是否正确
- 测试 refresh_token 是否有效
- 检查 IMAP 连接是否正常

---

#### 4. 邮件管理（管理员接口）

以下接口需要管理员认证（`Authorization: Bearer <token>`），主要用于管理后台。

##### 4.1 删除缓存邮件

**端点**: `DELETE /api/email/{email_account}/{message_id}`

**描述**: 删除 SQLite 缓存中的指定邮件（不保证同步删除远端邮箱）

**调用方 / 状态**:
- 管理后台：`EmailViewModal` 中的“删除邮件”按钮会调用此接口

##### 4.2 标记缓存邮件为已读

**端点**: `POST /api/email/{email_account}/{message_id}/read`

**描述**: 标记缓存中的邮件为已读（仅影响本地缓存状态）

**调用方 / 状态**:
- `deprecated/internal`：目前前端未使用，保留供未来扩展或外部工具调用

---

### 账户管理

所有账户管理接口都需要管理员认证（JWT token）。

#### 1. 获取所有账户列表

**端点**: `GET /api/accounts`

**描述**: 获取所有已配置的邮箱账户列表

**认证**: 需要管理员认证

**响应**:
```json
{
  "success": true,
  "data": [
    {"email": "user1@example.com"},
    {"email": "user2@example.com"}
  ],
  "message": "共 2 个账户"
}
```

**示例**:
```bash
curl "http://localhost:5001/api/accounts" \
  -H "Authorization: Bearer {access_token}"
```


---

#### 2. 分页获取账户列表

**端点**: `GET /api/accounts/paged`

**描述**: 分页获取账户列表，支持搜索

**认证**: 需要管理员认证

**查询参数**:
- `q` (可选): 按邮箱子串搜索（不区分大小写）
- `page` (可选): 页码（从 1 开始），默认为 1
- `page_size` (可选): 每页数量（10/20/50/100），默认为 10

**响应**:
```json
{
  "success": true,
  "data": {
    "items": [
      {"email": "user1@example.com"},
      {"email": "user2@example.com"}
    ],
    "total": 25,
    "page": 1,
    "page_size": 10
  },
  "message": "成功"
}
```

**前端增强功能** (v2.3.0):
- ✅ 页码选择器：显示当前页前后页码，中间用省略号（如 `1 ... 5 6 [7] 8 9 ... 20`）
- ✅ 每页数量选择器：下拉菜单快速切换（10/20/50/100）
- ✅ 跳转功能：输入框直接跳转到指定页（带验证）
- ✅ 总数统计：显示"共 X 条记录"
- ✅ 移动端响应式布局

**示例**:
```bash
# 获取第一页
curl "http://localhost:5001/api/accounts/paged?page=1&page_size=10" \
  -H "Authorization: Bearer {access_token}"

# 搜索包含 "gmail" 的账户
curl "http://localhost:5001/api/accounts/paged?q=gmail" \
  -H "Authorization: Bearer {access_token}"

# 获取每页 50 条的第 2 页
curl "http://localhost:5001/api/accounts/paged?page=2&page_size=50" \
  -H "Authorization: Bearer {access_token}"
```

---

#### 3. 批量导入账户

**端点**: `POST /api/import`

**描述**: 批量导入账户信息到数据库

**认证**: 需要管理员认证

**请求体**:
```json
{
  "accounts": [
    {
      "email": "user@example.com",
      "password": "password",
      "client_id": "client_id",
      "refresh_token": "refresh_token"
    }
  ],
  "merge_mode": "update"
}
```

**参数说明**:
- `accounts`: 账户列表数组
- `merge_mode`: 合并模式
  - `update`: 更新现有账户，添加新账户（默认）
  - `skip`: 跳过已存在的账户，只添加新账户
  - `replace`: 删除所有现有账户，导入新账户

**响应**:
```json
{
  "success": true,
  "total_count": 10,
  "added_count": 5,
  "updated_count": 3,
  "skipped_count": 2,
  "error_count": 0,
  "message": "导入成功：新增 5 个，更新 3 个，跳过 2 个",
  "details": [
    {
      "email": "user1@example.com",
      "action": "added",
      "message": "新增账户"
    }
  ]
}
```

**示例**:
```bash
curl -X POST "http://localhost:5001/api/import" \
  -H "Authorization: Bearer {access_token}" \
  -H "Content-Type: application/json" \
  -d '{
    "accounts": [
      {
        "email": "user@example.com",
        "refresh_token": "M.C123..."
      }
    ],
    "merge_mode": "update"
  }'
```

---

#### 4. 解析导入文本

**端点**: `POST /api/parse-import-text`

**描述**: 将文本格式的账户配置解析为 JSON 格式

**认证**: 需要管理员认证

**支持的格式**:
1. 标准格式: `邮箱----密码----refresh_token----client_id`
2. 简化格式: `邮箱----refresh_token`

**请求体**:
```json
{
  "text": "user1@example.com----password----refresh_token_abc----client_id_xyz\nuser2@example.com----refresh_token_def\n# 这是注释，会被忽略"
}
```

**响应**:
```json
{
  "success": true,
  "data": {
    "accounts": [
      {
        "email": "user1@example.com",
        "password": "password",
        "refresh_token": "refresh_token_abc",
        "client_id": "client_id_xyz"
      },
      {
        "email": "user2@example.com",
        "password": "",
        "refresh_token": "refresh_token_def",
        "client_id": "dbc8e03a-b00c-46bd-ae65-b683e7707cb0"
      }
    ],
    "parsed_count": 2,
    "errors": []
  },
  "message": "解析成功"
}
```

**示例**:
```bash
curl -X POST "http://localhost:5001/api/parse-import-text" \
  -H "Authorization: Bearer {access_token}" \
  -H "Content-Type: application/json" \
  -d '{
    "text": "user@example.com----M.C123..."
  }'
```

---

#### 创建单个账户

**端点**: `POST /api/accounts`

**描述**: 通过接口创建一个账户，密码与 refresh_token 自动加密

**请求体**:
```json
{
  "email": "user@example.com",
  "password": "",
  "client_id": "",
  "refresh_token": "M.C123..."
}
```

**响应**:
```json
{
  "success": true,
  "message": "账户已创建",
  "data": { "email": "user@example.com" }
}
```

---

#### 获取账户详情

**端点**: `GET /api/accounts/{email}`

**描述**: 返回账户的客户端 ID 以及敏感字段是否存在（附带脱敏预览）

**响应**:
```json
{
  "success": true,
  "data": {
    "email": "user@example.com",
    "client_id": "dbc8e03a-b00c-46bd-ae65-b683e7707cb0",
    "has_password": true,
    "has_refresh_token": true,
    "password_preview": "pa***rd",
    "refresh_token_preview": "M.***123"
  }
}
```

---

#### 更新账户

**端点**: `PUT /api/accounts/{email}`

**描述**: 覆盖指定账户的客户端 ID/密码/refresh_token，`email` 需与路径一致

**请求体**: 与创建接口相同

**响应**:
```json
{
  "success": true,
  "message": "账户已更新",
  "data": { "email": "user@example.com" }
}
```

---

#### 删除账户

**端点**: `DELETE /api/accounts/{email}`

**描述**: 删除账户及其标签、缓存记录

**响应**:
```json
{
  "success": true,
  "message": "账户已删除",
  "data": { "email": "user@example.com" }
}
```

---

#### 5. 导出账户配置

**端点**: `GET /api/export`

**描述**: 导出所有账户配置为文本文件

**认证**: 需要管理员认证

**查询参数**:
- `format` (可选): 导出格式，目前仅支持 "txt"，默认为 "txt"

**响应**: 文本文件下载

**示例**:
```bash
curl "http://localhost:5001/api/export?format=txt" \
  -H "Authorization: Bearer {access_token}" \
  -o accounts.txt
```

**⚠️ 安全提示**: 导出的文件包含所有账户的敏感信息（包括 refresh_token），请妥善保管。

---

### 标签管理

所有标签管理接口都需要管理员认证（JWT token）。

#### 1. 获取所有标签

**端点**: `GET /api/accounts/tags`

**描述**: 获取系统中所有的标签列表，以及每个账户对应的标签

**认证**: 需要管理员认证

**响应**:
```json
{
  "success": true,
  "data": {
    "tags": ["重要", "工作", "个人"],
    "accounts": {
      "user1@example.com": ["重要", "工作"],
      "user2@example.com": ["个人"]
    }
  },
  "message": "成功"
}
```

**示例**:
```bash
curl "http://localhost:5001/api/accounts/tags" \
  -H "Authorization: Bearer {access_token}"
```

---

#### 2. 获取指定账户的标签

**端点**: `GET /api/accounts/{email}/tags`

**描述**: 获取指定账户的标签列表

**认证**: 需要管理员认证

**路径参数**:
- `email`: 邮箱地址

**响应**:
```json
{
  "success": true,
  "data": {
    "email": "user@example.com",
    "tags": ["重要", "工作"]
  },
  "message": "成功"
}
```

**示例**:
```bash
curl "http://localhost:5001/api/accounts/user@example.com/tags" \
  -H "Authorization: Bearer {access_token}"
```


---

#### 3. 设置账户标签

**端点**: `POST /api/accounts/{email}/tags`

**描述**: 为指定账户设置标签列表

**认证**: 需要管理员认证

**路径参数**:
- `email`: 邮箱地址

**请求体**:
```json
{
  "email": "user@example.com",
  "tags": ["重要", "工作", "VIP"]
}
```

**参数说明**:
- `email`: 邮箱地址（必需）
- `tags`: 标签列表（字符串数组）

**响应**:
```json
{
  "success": true,
  "data": {
    "email": "user@example.com",
    "tags": ["重要", "工作", "VIP"]
  },
  "message": "标签设置成功"
}
```

**示例**:
```bash
curl -X POST "http://localhost:5001/api/accounts/user@example.com/tags" \
  -H "Authorization: Bearer {access_token}" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "tags": ["重要", "工作"]
  }'
```

**注意**:
- 设置标签会覆盖该账户的所有现有标签
- 传入空数组 `[]` 可以清除所有标签
- 标签名称区分大小写

---

### 系统配置

所有系统配置接口都需要管理员认证（JWT token）。

#### 1. 获取系统配置

**端点**: `GET /api/system/config`

**描述**: 获取系统配置信息

**认证**: 需要管理员认证

**响应**:
```json
{
  "success": true,
  "data": {
    "email_limit": 1
  },
  "message": "成功"
}
```

**配置项说明**:
- `email_limit`: 默认获取邮件数量（1-50）

**示例**:
```bash
curl "http://localhost:5001/api/system/config" \
  -H "Authorization: Bearer {access_token}"
```

---

#### 2. 更新系统配置

**端点**: `POST /api/system/config`

**描述**: 更新系统配置

**认证**: 需要管理员认证

**请求体**:
```json
{
  "email_limit": 5
}
```

**参数说明**:
- `email_limit`: 邮件获取数量限制（1-50）

**响应**:
```json
{
  "success": true,
  "message": "系统配置更新成功"
}
```

**示例**:
```bash
curl -X POST "http://localhost:5001/api/system/config" \
  -H "Authorization: Bearer {access_token}" \
  -H "Content-Type: application/json" \
  -d '{
    "email_limit": 5
  }'
```

**注意**:
- `email_limit` 的值必须在 1-50 之间
- 配置更新后立即生效
- 影响所有未指定 `top` 参数的邮件查询请求

---

#### 3. 刷新缓存

**端点**: `POST /api/system/cache/refresh`

**描述**: 清空邮件缓存并刷新账户缓存，确保最新配置立即生效

**认证**: 需要管理员认证

**响应**:
```json
{
  "success": true,
  "message": "缓存已刷新"
}
```

**示例**:
```bash
curl -X POST "http://localhost:5001/api/system/cache/refresh" \
  -H "Authorization: Bearer {access_token}"
```

**说明**:
- 该操作会移除 `email_cache` 中的所有记录
- 同时使账户缓存失效，下一次请求将重新加载数据库中的账户
- 适合刷新 config.txt 导入/替换后的场景

---

## 数据模型

### EmailMessage

邮件消息对象

```typescript
{
  message_id: string;      // 邮件唯一标识符
  subject: string;         // 邮件主题
  sender: string;          // 发件人邮箱地址
  received_date: string;   // 接收时间（ISO 8601 格式）
  body_preview: string;    // 邮件预览文本（前 100 字符）
  body_content: string;    // 完整邮件内容（HTML 或纯文本）
  body_type: string;       // 内容类型："html" 或 "text"
}
```

**示例**:
```json
{
  "message_id": "AAMkAGI1AAA=",
  "subject": "欢迎使用 Outlook 邮件管理系统",
  "sender": "noreply@example.com",
  "received_date": "2024-11-19T10:30:00",
  "body_preview": "感谢您使用我们的服务...",
  "body_content": "<html><body><h1>欢迎</h1><p>感谢您使用我们的服务...</p></body></html>",
  "body_type": "html"
}
```

---

### ApiResponse

通用 API 响应对象

```typescript
{
  success: boolean;        // 请求是否成功
  data?: any;             // 响应数据（可选）
  message?: string;       // 响应消息（可选）
}
```

**成功响应示例**:
```json
{
  "success": true,
  "data": {...},
  "message": "操作成功"
}
```

**失败响应示例**:
```json
{
  "success": false,
  "message": "操作失败：邮箱地址不存在"
}
```

---

### ImportAccountData

导入账户数据对象

```typescript
{
  email: string;           // 邮箱地址（必需）
  password?: string;       // 邮箱密码（可选）
  client_id?: string;      // OAuth2 客户端 ID（可选，默认使用系统配置）
  refresh_token: string;   // OAuth2 refresh token（必需）
}
```

**示例**:
```json
{
  "email": "user@example.com",
  "password": "password123",
  "client_id": "dbc8e03a-b00c-46bd-ae65-b683e7707cb0",
  "refresh_token": "M.C123_BAY.-CRud..."
}
```

---

### ImportResult

导入结果对象

```typescript
{
  success: boolean;        // 导入是否成功
  total_count: number;     // 总账户数
  added_count: number;     // 新增账户数
  updated_count: number;   // 更新账户数
  skipped_count: number;   // 跳过账户数
  error_count: number;     // 错误账户数
  message: string;         // 结果消息
  details: Array<{         // 详细信息
    email: string;
    action: string;        // "added" | "updated" | "skipped" | "error"
    message: string;
  }>;
}
```

---

### AdminLoginRequest

管理员登录请求对象

```typescript
{
  username: string;        // 用户名
  password: string;        // 密码
}
```

---

### AdminLoginResponse

管理员登录响应对象

```typescript
{
  access_token: string;    // JWT access token
  token_type: string;      // Token 类型（固定为 "bearer"）
  expires_in: number;      // 过期时间（秒）
}

### SystemConfigRequest

系统配置请求对象

```typescript
{
  email_limit: number;   // 默认获取邮件数量（1-50）
}
```

---

### AccountTagRequest

账户标签请求对象

```typescript
{
  email: string;         // 邮箱地址
  tags: string[];        // 标签列表
}
```

---

### TempAccountRequest

临时账户请求对象

```typescript
{
  email: string;         // 邮箱地址
  password?: string;     // 邮箱密码（可选）
  client_id?: string;    // OAuth2 客户端 ID（可选）
  refresh_token: string; // OAuth2 refresh token（必需）
  top?: number;          // 获取邮件数量（默认 5）
}
```

---

### TestEmailRequest

测试邮件请求对象

```typescript
{
  email: string;         // 邮箱地址
  password?: string;     // 邮箱密码（可选）
  client_id?: string;    // OAuth2 客户端 ID（可选）
  refresh_token?: string;// OAuth2 refresh token（可选，如不提供则使用配置中的）
}
```

---

## 错误处理

### 错误响应策略

本 API 使用两种错误响应方式，请根据不同场景正确处理：

#### 1. HTTP 状态码错误（4xx/5xx）

**适用场景**：
- 认证失败（401）
- 请求参数验证失败（422）
- 资源不存在（404）
- 服务器内部错误（500）

**特点**：
- HTTP 状态码为非 200
- 响应格式为 FastAPI 标准错误格式（包含 `detail` 字段）
- 前端应在 axios 拦截器的 error 回调中捕获

**示例**：401 认证失败会返回状态码 401 和 `{"detail": "未提供认证令牌"}`

#### 2. 业务逻辑错误（200 + success: false）

**适用场景**：
- 邮箱未配置
- 邮件获取失败
- 导入/导出失败
- 其他业务层面的错误

**特点**：
- HTTP 状态码为 200
- 响应格式为 `ApiResponse` 模型：`{"success": false, "message": "错误信息"}`
- 前端应检查 `response.data.success` 字段判断业务成功与否

**示例**：邮箱未配置会返回 200 状态码和 `{"success": false, "message": "未在配置中找到该邮箱"}`

### HTTP 状态码

API 使用标准的 HTTP 状态码：

- `200 OK`: 请求成功（注意：业务失败仍可能返回 200，需检查 `success` 字段）
- `400 Bad Request`: 请求参数错误
- `401 Unauthorized`: 未授权或认证失败
- `404 Not Found`: 资源不存在（某些业务场景下会返回 200 + success: false）
- `422 Unprocessable Entity`: 请求参数验证失败
- `429 Too Many Requests`: 频率限制（登录失败次数过多）
- `500 Internal Server Error`: 服务器内部错误

### 错误响应格式

**认证错误**:
```json
{
  "detail": "未提供认证令牌"
}
```

**参数验证错误**:
```json
{
  "detail": [
    {
      "loc": ["body", "email"],
      "msg": "field required",
      "type": "value_error.missing"
    }
  ]
}
```

**业务逻辑错误**:
```json
{
  "success": false,
  "message": "邮箱地址不存在或 refresh_token 无效"
}
```

### 常见错误及解决方案

#### 1. 401 Unauthorized

**错误**: `未提供认证令牌` 或 `无效或过期的令牌`

**原因**:
- 未提供 Authorization header
- Token 格式错误
- Token 已过期
- Token 无效

**解决方案**:
```bash
# 重新登录获取新的 token
curl -X POST "http://localhost:5001/api/admin/login" \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "<your-admin-password>"}'

# 使用新 token 发起请求
curl "http://localhost:5001/api/accounts" \
  -H "Authorization: Bearer {new_access_token}"
```

---

#### 2. Refresh Token 过期

**错误**: `邮箱 xxx 的 Refresh Token 已过期`

**原因**: Microsoft OAuth2 refresh token 已过期（通常 90 天）

**解决方案**:
1. 使用 `get_refresh_token.py` 重新获取授权
2. 更新数据库中的 refresh_token

```bash
# 运行获取 refresh token 脚本
python get_refresh_token.py

# 通过管理后台导入新的 refresh_token
```

---

#### 3. IMAP 连接失败

**错误**: `IMAP 连接失败` 或 `认证失败`

**原因**:
- Refresh token 无效
- Access token 获取失败
- IMAP 服务器连接问题
- 网络问题

**解决方案**:
1. 检查 refresh_token 是否有效
2. 使用 `/api/test-email` 接口测试连接
3. 查看服务器日志获取详细错误信息

---

## 示例代码

### Python 示例

#### 1. 管理员登录并获取账户列表

```python
import requests

# 基础 URL
BASE_URL = "http://localhost:5001"

# 1. 登录获取 token
login_response = requests.post(
    f"{BASE_URL}/api/admin/login",
    json={
        "username": "admin",
        "password": "<your-admin-password>"
    }
)
login_data = login_response.json()
access_token = login_data["access_token"]

# 2. 获取账户列表
headers = {"Authorization": f"Bearer {access_token}"}
accounts_response = requests.get(
    f"{BASE_URL}/api/accounts",
    headers=headers
)
accounts = accounts_response.json()
print(f"账户列表: {accounts}")
```


#### 2. 获取邮件列表（Python 示例）

```python
import requests

BASE_URL = "http://localhost:5001"

# 获取指定邮箱的最近 5 封邮件
params = {
    "email": "user@example.com",
    "top": 5,
}
response = requests.get(f"{BASE_URL}/api/messages", params=params)

if response.ok:
    data = response.json()
    for msg in data.get("data", []):
        print(msg["received_date"], msg["subject"])
else:
    print("请求失败", response.status_code, response.text)
```
