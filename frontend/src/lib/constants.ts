/**
 * 应用程序常量配置
 */

// ============================================================================
// 配置常量
// ============================================================================

export const CONFIG = {
  DEFAULT_PAGE_SIZE: 10,
  MAX_PAGE_SIZE: 100,
  DEFAULT_EMAIL_LIMIT: 5,
  MAX_EMAIL_LIMIT: 50,
  TOAST_DURATION: 3000,
} as const;

// ============================================================================
// 时间相关常量
// ============================================================================

export const TIMING = {
  /** 搜索防抖延迟（毫秒）*/
  DEBOUNCE_DELAY: 500,
  /** Token 过期时间偏移量（毫秒），用于提前刷新 */
  TOKEN_CLOCK_SKEW: 60_000,
  // 注意：Toast 显示时长请使用 CONFIG.TOAST_DURATION
  /** 轮询间隔（毫秒）*/
  POLL_INTERVAL: 30_000,
  /** 自动刷新间隔（毫秒）*/
  AUTO_REFRESH_INTERVAL: 60_000,
} as const;

// ============================================================================
// 请求重试配置
// ============================================================================

export const RETRY_CONFIG = {
  /** 最大重试次数 */
  MAX_RETRIES: 3,
  /** 基础重试延迟（毫秒）*/
  RETRY_DELAY: 1000,
  /** 请求超时时间（毫秒）*/
  REQUEST_TIMEOUT: 30_000,
} as const;

// ============================================================================
// 错误消息
// ============================================================================

export const MESSAGES = {
  // 登录相关
  ERROR_LOGIN_FAILED: '登录失败，请检查用户名或密码',
  ERROR_TOKEN_EXPIRED: '登录已过期，请重新登录',
  ERROR_NETWORK: '网络请求失败',

  // 账户管理
  ERROR_ACCOUNT_LOAD_FAILED: '加载账户列表失败',
  ERROR_ACCOUNT_CREATE_FAILED: '创建账户失败',
  ERROR_ACCOUNT_UPDATE_FAILED: '更新账户失败',
  ERROR_ACCOUNT_DELETE_FAILED: '删除账户失败',
  ERROR_BATCH_DELETE_FAILED: '批量删除失败',

  // 导入导出
  ERROR_IMPORT_PARSE_FAILED: '解析失败',
  ERROR_IMPORT_FAILED: '导入失败',
  ERROR_EXPORT_FAILED: '导出失败',
  SUCCESS_IMPORT: '导入成功',
  SUCCESS_EXPORT: '导出成功',
  SUCCESS_CACHE_REFRESHED: '缓存刷新成功',
  ERROR_CACHE_REFRESH_FAILED: '缓存刷新失败',

  // 标签管理
  ERROR_TAG_INPUT_REQUIRED: '请输入至少一个标签',
  ERROR_TAG_SAVE_FAILED: '标签保存失败',
  ERROR_BATCH_TAG_OPERATION_FAILED: '批量标签操作失败',
  SUCCESS_TAG_SAVED: '标签保存成功',

  // 系统配置
  ERROR_CONFIG_UPDATE_FAILED: '配置更新失败',
  SUCCESS_CONFIG_UPDATED: '配置更新成功',

  // 邮件相关
  ERROR_EMAIL_FETCH_FAILED: '获取邮件失败',
  ERROR_EMAIL_NOT_FOUND: '未找到邮件',
  ERROR_EMAIL_NOT_CONFIGURED: '该邮箱未配置。请提供 Refresh Token 使用临时模式，或联系管理员。',

  // 通用
  ERROR_UNKNOWN: '操作失败',
  SUCCESS_OPERATION: '操作成功',
  GENERIC_ERROR: '发生未知错误，请稍后重试',
} as const;

// ============================================================================
// UI 文案
// ============================================================================

export const UI_TEXT = {
  // 按钮
  BUTTON_LOGIN: '登 录',
  BUTTON_LOGOUT: '退出',
  BUTTON_IMPORT: '导入',
  BUTTON_EXPORT: '导出',
  BUTTON_SAVE: '保存',
  BUTTON_CANCEL: '取消',
  BUTTON_CONFIRM: '确认',
  BUTTON_REFRESH: '刷新',
  BUTTON_SEARCH: '搜索',
  BUTTON_CLOSE: '关闭',

  // 标题
  TITLE_ADMIN_DASHBOARD: 'Outlooker',
  TITLE_ADMIN_LOGIN: '管理员登录',
  TITLE_VERIFICATION: 'Outlook 验证码提取',
  TITLE_IMPORT_ACCOUNTS: '批量导入账户',

  // 占位符
  PLACEHOLDER_SEARCH_EMAIL: '搜索邮箱...',
  PLACEHOLDER_EMAIL: 'example@outlook.com',
  PLACEHOLDER_PASSWORD: '请输入密码',
  PLACEHOLDER_IMPORT_TEXT: '请粘贴账户数据，每行一条...',

  // 状态
  STATUS_LOADING: '加载中...',
  STATUS_SAVING: '保存中...',
  STATUS_IMPORTING: '导入中...',
  STATUS_EXPORTING: '导出中...',

  // 其他
  NO_DATA: '暂无数据',
  NO_EMAILS: '该邮箱暂无邮件',
  LOADING_FAILED: '加载失败，请重试',
} as const;

// ============================================================================
// 路由路径
// ============================================================================

export const ROUTES = {
  HOME: '/',
  ADMIN_LOGIN: '/admin/login',
  ADMIN_DASHBOARD: '/admin',
} as const;

// ============================================================================
// API 路径配置
// ============================================================================

/**
 * API 路径前缀，用于判断请求类型
 */
export const API_PATHS = {
  /** 公共 API 路径前缀（需要 X-Public-Token） */
  PUBLIC: [
    '/api/public',
    'api/public',
    '/api/messages',
    'api/messages',
    '/api/temp-messages',
    'api/temp-messages',
    '/api/test-email',
    'api/test-email',
  ],
  /** 管理员受保护 API 路径前缀（需要 Bearer Token） */
  ADMIN: [
    '/api/accounts',
    'api/accounts',
    '/api/import',
    'api/import',
    '/api/export',
    'api/export',
    '/api/system',
    'api/system',
    '/api/parse-import-text',
    'api/parse-import-text',
    '/api/tags',
    'api/tags',
  ],
} as const;

/**
 * 开发环境默认 Token
 * 生产环境应通过环境变量 VITE_PUBLIC_API_TOKEN 配置
 */
export const DEV_PUBLIC_TOKEN = 'dev-public-token-change-me';

// Type exports
export type ConfigKey = keyof typeof CONFIG;
export type MessageKey = keyof typeof MESSAGES;
export type UITextKey = keyof typeof UI_TEXT;
export type RouteKey = keyof typeof ROUTES;
