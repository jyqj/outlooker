#!/usr/bin/env python3
"""
应用版本信息

此模块定义应用的版本号，供其他模块统一引用。
"""

__version__ = "2.4.0"

# 版本信息详情
VERSION_INFO = {
    "major": 2,
    "minor": 4,
    "patch": 0,
    "release": "stable",
}


def get_version() -> str:
    """获取版本号字符串"""
    return __version__


def get_version_info() -> dict:
    """获取版本详细信息"""
    return {
        **VERSION_INFO,
        "version": __version__,
    }
