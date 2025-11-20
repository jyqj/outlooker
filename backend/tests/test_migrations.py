#!/usr/bin/env python3
"""数据库迁移系统测试"""

import sqlite3
import pytest
from pathlib import Path
import tempfile

from app.migrations import (
    register_migration,
    apply_migrations,
    _normalize_registry,
    Migration,
    _REGISTRY
)


@pytest.fixture
def temp_db():
    """创建临时数据库用于测试"""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name

    conn = sqlite3.connect(db_path)

    # 创建基础表结构(模拟database.py的init_database)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS system_config (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()

    yield conn

    conn.close()
    Path(db_path).unlink(missing_ok=True)


class TestMigrationRegistry:
    """测试迁移注册功能"""

    def test_register_migration_decorator(self):
        """测试迁移注册装饰器"""
        initial_count = len(_REGISTRY)
        
        @register_migration("test_001", "Test migration")
        def test_migration(conn: sqlite3.Connection):
            pass
        
        # 验证迁移已注册
        assert len(_REGISTRY) > initial_count
        
        # 查找注册的迁移
        test_migrations = [m for m in _REGISTRY if m.version == "test_001"]
        assert len(test_migrations) > 0
        assert test_migrations[0].description == "Test migration"

    def test_normalize_registry_sorts_by_version(self):
        """测试迁移按版本排序"""
        migrations = [
            Migration("003", "Third", lambda c: None),
            Migration("001", "First", lambda c: None),
            Migration("002", "Second", lambda c: None),
        ]
        
        normalized = _normalize_registry(migrations)
        
        assert len(normalized) == 3
        assert normalized[0].version == "001"
        assert normalized[1].version == "002"
        assert normalized[2].version == "003"

    def test_normalize_registry_removes_duplicates(self):
        """测试去重功能"""
        def dummy_handler(c):
            pass
        
        migrations = [
            Migration("001", "First", dummy_handler),
            Migration("001", "Duplicate", dummy_handler),
            Migration("002", "Second", dummy_handler),
        ]
        
        normalized = _normalize_registry(migrations)
        
        # 应该只保留第一个001版本
        assert len(normalized) == 2
        assert normalized[0].version == "001"
        assert normalized[0].description == "First"
        assert normalized[1].version == "002"


class TestMigrationExecution:
    """测试迁移执行功能"""

    def test_apply_migrations_creates_schema_table(self, temp_db):
        """测试迁移系统创建schema_migrations表"""
        apply_migrations(temp_db)
        
        cursor = temp_db.cursor()
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name='schema_migrations'
        """)
        result = cursor.fetchone()
        
        assert result is not None
        assert result[0] == "schema_migrations"

    def test_apply_migrations_executes_new_migrations(self, temp_db):
        """测试执行新迁移"""
        # 注册测试迁移
        executed = []
        
        @register_migration("test_exec_001", "Test execution")
        def test_exec_migration(conn: sqlite3.Connection):
            executed.append("test_exec_001")
            cursor = conn.cursor()
            cursor.execute("CREATE TABLE test_table (id INTEGER PRIMARY KEY)")
        
        # 执行迁移
        apply_migrations(temp_db)
        
        # 验证迁移已执行
        assert "test_exec_001" in executed
        
        # 验证表已创建
        cursor = temp_db.cursor()
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name='test_table'
        """)
        result = cursor.fetchone()
        assert result is not None

    def test_apply_migrations_skips_applied_migrations(self, temp_db):
        """测试跳过已应用的迁移"""
        # 手动标记迁移为已应用
        cursor = temp_db.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS schema_migrations (
                version TEXT PRIMARY KEY,
                applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cursor.execute(
            "INSERT INTO schema_migrations (version) VALUES (?)",
            ("test_skip_001",)
        )
        temp_db.commit()
        
        # 注册相同版本的迁移
        executed = []
        
        @register_migration("test_skip_001", "Should be skipped")
        def test_skip_migration(conn: sqlite3.Connection):
            executed.append("test_skip_001")
        
        # 执行迁移
        apply_migrations(temp_db)
        
        # 验证迁移未执行
        assert "test_skip_001" not in executed

    def test_apply_migrations_records_applied_version(self, temp_db):
        """测试迁移版本记录"""
        @register_migration("test_record_001", "Test recording")
        def test_record_migration(conn: sqlite3.Connection):
            pass
        
        # 执行迁移
        apply_migrations(temp_db)
        
        # 验证版本已记录
        cursor = temp_db.cursor()
        cursor.execute(
            "SELECT version FROM schema_migrations WHERE version = ?",
            ("test_record_001",)
        )
        result = cursor.fetchone()
        
        assert result is not None
        assert result[0] == "test_record_001"


class TestBuiltInMigrations:
    """测试内置迁移"""

    def test_system_metrics_table_migration(self, temp_db):
        """测试system_metrics表创建迁移"""
        # 执行所有迁移
        apply_migrations(temp_db)
        
        # 验证system_metrics表已创建
        cursor = temp_db.cursor()
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name='system_metrics'
        """)
        result = cursor.fetchone()
        assert result is not None
        
        # 验证索引已创建
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='index' AND name='idx_system_metrics_updated_at'
        """)
        result = cursor.fetchone()
        assert result is not None

    def test_email_limit_default_config_migration(self, temp_db):
        """测试email_limit默认配置迁移"""
        # system_config表已在fixture中创建

        # 执行迁移
        apply_migrations(temp_db)

        # 验证email_limit配置已写入
        cursor = temp_db.cursor()
        cursor.execute(
            "SELECT value FROM system_config WHERE key = 'email_limit'"
        )
        result = cursor.fetchone()

        # 迁移应该写入默认值
        assert result is not None
        assert result[0] is not None

