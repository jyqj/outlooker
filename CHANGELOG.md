# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [2.2.1] - 2025-01-20

### 🎯 代码质量改进

#### 重构
- **删除冗余代码**: 移除了730行的冗余 `backend/app/services.py` 文件
  - 所有功能已迁移到模块化的 `backend/app/services/` 目录
  - 提升了代码可维护性和清晰度
  - 确保单一数据源原则(Single Source of Truth)

#### 测试覆盖提升
- **后端测试**: 从63个测试增加到95个测试 (+51%)
  - 新增 `test_jwt_auth.py`: JWT认证和密码哈希测试(15个测试)
  - 新增 `test_database.py`: 数据库CRUD操作测试(9个测试)
  - 新增 `test_migrations.py`: 数据库迁移系统测试(8个测试)
  - 测试通过率: 100% (95 passed, 1 skipped)

- **前端测试**: 通过率从56%提升到100%
  - 创建缺失的 `Alert.jsx` UI组件
  - 修复了ImportModal和AdminDashboardPage的测试依赖问题
  - 测试通过率: 100% (23 passed)

#### 测试覆盖的关键领域
- ✅ JWT认证和授权机制
- ✅ 密码哈希和验证(bcrypt)
- ✅ 数据库CRUD操作
- ✅ 数据库迁移系统
- ✅ 账户导入和合并逻辑
- ✅ 系统配置管理
- ✅ 数据加密和解密(Fernet)
- ✅ React组件渲染和交互

### 📊 统计数据

| 指标 | 改进前 | 改进后 | 提升 |
|------|--------|--------|------|
| 后端测试数量 | 63 | 95 | +51% |
| 前端测试通过率 | 56% | 100% | +44% |
| 总测试数量 | 79 | 118 | +49% |
| 代码冗余 | 730行重复 | 0 | -100% |

### 🔧 技术改进
- 改进了测试隔离性(使用临时数据库和fixture)
- 增强了测试的可读性和可维护性
- 统一了测试命名规范和组织结构

---

## [2.2.0] - 2025-01-15

### Added
- 完整的JWT认证系统
- 数据加密存储(Fernet)
- 登录频率限制和审计日志
- React 19前端重构
- Docker容器化部署支持

### Changed
- 升级到Python 3.12
- 升级到React 19
- 重构服务层为模块化架构

### Security
- 实现bcrypt密码哈希
- 添加CORS白名单控制
- 敏感数据加密存储

---

## [2.1.0] - 2024-12-01

### Added
- 批量账户导入/导出功能
- 账户标签管理
- 系统配置面板
- 缓存管理功能

### Improved
- 优化IMAP连接复用
- 改进邮件缓存机制
- 提升前端性能

---

## [2.0.0] - 2024-11-01

### Added
- 全新的管理后台界面
- 验证码自动提取功能
- 多账户支持
- 邮件分页和搜索

### Changed
- 重构为前后端分离架构
- 采用FastAPI替代Flask
- 使用React替代传统模板引擎

---

## [1.0.0] - 2024-10-01

### Added
- 初始版本发布
- 基础邮件查看功能
- 简单的账户管理
- SQLite数据存储

