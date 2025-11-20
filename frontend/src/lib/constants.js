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
};

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
  
  // 导入导出
  ERROR_IMPORT_PARSE_FAILED: '解析失败',
  ERROR_IMPORT_FAILED: '导入失败',
  ERROR_EXPORT_FAILED: '导出失败',
  SUCCESS_IMPORT: '导入成功',
  SUCCESS_EXPORT: '导出成功',
  SUCCESS_CACHE_REFRESHED: '缓存刷新成功',
  ERROR_CACHE_REFRESH_FAILED: '缓存刷新失败',
  
  // 标签管理
  ERROR_TAG_SAVE_FAILED: '标签保存失败',
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
};

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
};

// ============================================================================
// 路由路径
// ============================================================================

export const ROUTES = {
  HOME: '/',
  ADMIN_LOGIN: '/admin/login',
  ADMIN_DASHBOARD: '/admin',
};
