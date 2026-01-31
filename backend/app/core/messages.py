#!/usr/bin/env python3
"""
应用程序消息常量
集中管理所有用户可见的错误消息、提示信息等文案
"""

# ============================================================================
# 错误消息 - 认证相关
# ============================================================================

ERROR_AUTH_NO_TOKEN = "未提供认证令牌"
ERROR_AUTH_INVALID_FORMAT = "无效的认证格式"
ERROR_AUTH_INVALID_TOKEN = "无效或过期的令牌"
ERROR_AUTH_MISSING_USER = "令牌中缺少用户信息"
ERROR_AUTH_FAILED = "认证失败"

# ============================================================================
# 错误消息 - 账户相关
# ============================================================================

ERROR_EMAIL_NOT_CONFIGURED = "未在配置中找到该邮箱"
ERROR_EMAIL_NOT_PROVIDED = "邮箱地址不能为空"
ERROR_EMAIL_INVALID = "邮箱地址格式不正确"
ERROR_ACCOUNT_EXISTS = "账户已存在"
ERROR_ACCOUNT_NOT_EXISTS = "账户不存在"
ERROR_ACCOUNT_CREATE_FAILED = "创建账户失败"
ERROR_ACCOUNT_UPDATE_FAILED = "更新账户失败"
ERROR_ACCOUNT_DELETE_FAILED = "删除账户失败"

# ============================================================================
# 错误消息 - 邮件相关
# ============================================================================

ERROR_MESSAGES_FETCH_FAILED = "获取邮件失败"
ERROR_MESSAGE_NOT_FOUND = "未找到邮件"
ERROR_EMAIL_CONNECTION_FAILED = "邮件连接失败"
ERROR_REFRESH_TOKEN_EXPIRED = "Refresh Token 已过期"
ERROR_REFRESH_TOKEN_INVALID = "Refresh Token 无效"

# ============================================================================
# 错误消息 - 导入导出相关
# ============================================================================

ERROR_IMPORT_FAILED = "导入失败"
ERROR_IMPORT_NO_DATA = "没有找到有效的账户数据"
ERROR_IMPORT_PARSE_FAILED = "解析导入文本失败"
ERROR_EXPORT_FAILED = "导出失败"
ERROR_EXPORT_NO_ACCOUNTS = "暂无账户数据"

# ============================================================================
# 错误消息 - 系统配置相关
# ============================================================================

ERROR_CONFIG_UPDATE_FAILED = "更新系统配置失败"
ERROR_CONFIG_INVALID_VALUE = "配置值无效"
ERROR_EMAIL_LIMIT_INVALID = "邮件限制必须在1-50之间"

# ============================================================================
# 错误消息 - 标签相关
# ============================================================================

ERROR_TAGS_GET_FAILED = "获取标签失败"
ERROR_TAGS_SET_FAILED = "保存标签失败"
ERROR_TAGS_EMAIL_MISMATCH = "邮箱不一致"

# ============================================================================
# 成功消息
# ============================================================================

SUCCESS_ACCOUNT_CREATED = "账户已创建"
SUCCESS_ACCOUNT_UPDATED = "账户已更新"
SUCCESS_ACCOUNT_DELETED = "账户已删除"
SUCCESS_TAGS_SAVED = "标签已保存"
SUCCESS_CONFIG_UPDATED = "系统配置更新成功"
SUCCESS_IMPORT_COMPLETED = "导入成功"
SUCCESS_EXPORT_COMPLETED = "导出成功"

# ============================================================================
# 信息提示
# ============================================================================

INFO_NO_MESSAGES = "该邮箱暂无邮件"
INFO_CONNECTION_SUCCESS = "连接成功"
INFO_PARSING_SUCCESS = "解析成功"
