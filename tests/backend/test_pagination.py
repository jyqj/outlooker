#!/usr/bin/env python3
"""
分页工具单元测试

测试 pagination 模块中的分页和搜索功能
"""

import pytest

from app.utils.pagination import (
    normalize_email,
    paginate_items,
    filter_messages_by_search,
)


class TestNormalizeEmail:
    """测试邮箱规范化函数"""

    def test_normalize_simple_email(self):
        """测试规范化简单邮箱"""
        result = normalize_email("User@Example.com")
        assert result == "user@example.com"

    def test_normalize_email_with_spaces(self):
        """测试去除邮箱两端空格"""
        result = normalize_email("  user@example.com  ")
        assert result == "user@example.com"

    def test_normalize_uppercase_email(self):
        """测试大写邮箱转小写"""
        result = normalize_email("USER@EXAMPLE.COM")
        assert result == "user@example.com"

    def test_normalize_empty_string(self):
        """测试空字符串"""
        result = normalize_email("")
        assert result == ""

    def test_normalize_none(self):
        """测试 None 值"""
        result = normalize_email(None)
        assert result == ""


class TestPaginateItems:
    """测试分页函数"""

    def test_paginate_first_page(self):
        """测试获取第一页"""
        items = list(range(25))
        result, total = paginate_items(items, page=1, page_size=10)

        assert result == list(range(10))
        assert total == 25

    def test_paginate_middle_page(self):
        """测试获取中间页"""
        items = list(range(25))
        result, total = paginate_items(items, page=2, page_size=10)

        assert result == list(range(10, 20))
        assert total == 25

    def test_paginate_last_page(self):
        """测试获取最后一页（不满页）"""
        items = list(range(25))
        result, total = paginate_items(items, page=3, page_size=10)

        assert result == [20, 21, 22, 23, 24]
        assert total == 25

    def test_paginate_beyond_range(self):
        """测试超出范围的页码"""
        items = list(range(10))
        result, total = paginate_items(items, page=5, page_size=10)

        assert result == []
        assert total == 10

    def test_paginate_invalid_page(self):
        """测试无效页码（0 或负数）"""
        items = list(range(10))
        
        # 页码 0 应该被修正为 1
        result, total = paginate_items(items, page=0, page_size=5)
        assert result == list(range(5))
        
        # 负数页码也应该被修正为 1
        result, total = paginate_items(items, page=-1, page_size=5)
        assert result == list(range(5))

    def test_paginate_invalid_page_size(self):
        """测试无效每页数量"""
        items = list(range(10))
        
        # page_size 0 应该被修正为 1
        result, total = paginate_items(items, page=1, page_size=0)
        assert result == [0]
        assert total == 10

    def test_paginate_empty_list(self):
        """测试空列表"""
        items = []
        result, total = paginate_items(items, page=1, page_size=10)

        assert result == []
        assert total == 0

    def test_paginate_single_item(self):
        """测试单个元素"""
        items = ["single"]
        result, total = paginate_items(items, page=1, page_size=10)

        assert result == ["single"]
        assert total == 1


class TestFilterMessagesBySearch:
    """测试邮件搜索过滤函数"""

    @pytest.fixture
    def sample_messages(self):
        """创建示例邮件列表"""
        return [
            {
                "subject": "Meeting Tomorrow",
                "from": {"emailAddress": {"address": "alice@example.com"}},
                "bodyPreview": "Please join the meeting at 10am",
            },
            {
                "subject": "Invoice #123",
                "from": {"emailAddress": {"address": "billing@company.com"}},
                "bodyPreview": "Your monthly invoice is attached",
            },
            {
                "subject": "Hello World",
                "from": {"emailAddress": {"address": "bob@example.com"}},
                "bodyPreview": "This is a test email",
            },
        ]

    def test_filter_by_subject(self, sample_messages):
        """测试按主题搜索"""
        result = filter_messages_by_search(sample_messages, "Meeting")
        
        assert len(result) == 1
        assert result[0]["subject"] == "Meeting Tomorrow"

    def test_filter_by_sender(self, sample_messages):
        """测试按发件人搜索"""
        result = filter_messages_by_search(sample_messages, "alice")
        
        assert len(result) == 1
        assert "alice" in result[0]["from"]["emailAddress"]["address"]

    def test_filter_by_body_preview(self, sample_messages):
        """测试按正文预览搜索"""
        result = filter_messages_by_search(sample_messages, "invoice")
        
        assert len(result) == 1
        assert "Invoice" in result[0]["subject"]

    def test_filter_case_insensitive(self, sample_messages):
        """测试大小写不敏感搜索"""
        result = filter_messages_by_search(sample_messages, "MEETING")
        
        assert len(result) == 1
        assert result[0]["subject"] == "Meeting Tomorrow"

    def test_filter_no_match(self, sample_messages):
        """测试无匹配结果"""
        result = filter_messages_by_search(sample_messages, "nonexistent")
        
        assert len(result) == 0

    def test_filter_empty_search(self, sample_messages):
        """测试空搜索词返回所有结果"""
        result = filter_messages_by_search(sample_messages, "")
        
        assert len(result) == 3

    def test_filter_none_search(self, sample_messages):
        """测试 None 搜索词返回所有结果"""
        result = filter_messages_by_search(sample_messages, None)
        
        assert len(result) == 3

    def test_filter_partial_match(self, sample_messages):
        """测试部分匹配"""
        result = filter_messages_by_search(sample_messages, "example.com")
        
        assert len(result) == 2  # alice 和 bob 都是 example.com

    def test_filter_missing_fields(self):
        """测试处理缺失字段的邮件"""
        messages = [
            {"subject": "Test"},  # 缺少 from 和 bodyPreview
            {},  # 空邮件
        ]
        
        # 不应该崩溃
        result = filter_messages_by_search(messages, "Test")
        assert len(result) == 1
