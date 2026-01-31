"""
通用校验工具模块

提供可复用的校验函数和常量
"""

import re

from ..core.exceptions import ValidationError

# 标签校验常量
MAX_TAG_LENGTH = 20
MAX_TAGS_COUNT = 10
INVALID_TAG_CHARS_PATTERN = re.compile(r'[<>&"\']')


def validate_tags(tags: list[str]) -> None:
    """
    验证标签列表是否符合规则
    
    Args:
        tags: 标签列表
        
    Raises:
        ValidationError: 如果标签不符合规则
    """
    if len(tags) > MAX_TAGS_COUNT:
        raise ValidationError(
            message=f"标签数量不能超过 {MAX_TAGS_COUNT} 个",
            field="tags"
        )

    for tag in tags:
        if not tag or not tag.strip():
            raise ValidationError(message="标签不能为空", field="tags")

        if len(tag) > MAX_TAG_LENGTH:
            raise ValidationError(
                message=f"标签 '{tag}' 长度超过 {MAX_TAG_LENGTH} 个字符",
                field="tags"
            )

        if INVALID_TAG_CHARS_PATTERN.search(tag):
            raise ValidationError(
                message=f"标签 '{tag}' 包含不允许的特殊字符 (< > & \" ')",
                field="tags"
            )
