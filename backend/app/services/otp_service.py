from __future__ import annotations

import re
from typing import Any, Dict, Optional


def _clean_html(html: str) -> str:
    """深度清理 HTML 内容，转换为纯文本。

    - 移除 <script>/<style> 及其内容
    - 移除所有标签
    - 解码常见 HTML 实体
    - 规范空白字符
    """
    if not html:
        return ""

    text = html

    # 1. 移除 script 和 style 标签及其内容
    text = re.sub(
        r"<script\b[^<]*(?:(?!<\/script>)<[^<]*)*<\/script>",
        " ",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(
        r"<style\b[^<]*(?:(?!<\/style>)<[^<]*)*<\/style>",
        " ",
        text,
        flags=re.IGNORECASE,
    )

    # 2. 移除所有 HTML 标签
    text = re.sub(r"<[^>]+>", " ", text)

    # 3. 解码常见 HTML 实体
    entities = {
        "&nbsp;": " ",
        "&lt;": "<",
        "&gt;": ">",
        "&amp;": "&",
        "&quot;": '"',
        "&#39;": "'",
        "&apos;": "'",
    }
    for entity, char in entities.items():
        text = text.replace(entity, char)

    # 4. 解码数字实体
    def _decode_dec(match: re.Match[str]) -> str:
        try:
            return chr(int(match.group(1)))
        except Exception:
            return match.group(0)

    def _decode_hex(match: re.Match[str]) -> str:
        try:
            return chr(int(match.group(1), 16))
        except Exception:
            return match.group(0)

    text = re.sub(r"&#(\d+);", _decode_dec, text)
    text = re.sub(r"&#x([0-9a-f]+);", _decode_hex, text, flags=re.IGNORECASE)

    # 5. 规范化空白字符
    text = re.sub(r"\s+", " ", text).strip()
    return text


_KEYWORDS = [
    # 英文关键词
    (re.compile(r"(?:verification|verify|security|confirmation|auth(?:entication)?)\s*code", re.I), 10),
    (re.compile(r"\b(?:otp|pin|passcode|token)\b", re.I), 9),
    (re.compile(r"\bcode\b", re.I), 7),
    # 中文关键词
    (re.compile(r"验证码|校验码|动态码|安全码|确认码"), 10),
]

_CODE_PATTERNS = [
    # 6位纯数字（最常见）
    (re.compile(r"(?:^|[^0-9A-Za-z])([0-9]{6})(?:[^0-9A-Za-z]|$)"), 10),
    # 4位纯数字
    (re.compile(r"(?:^|[^0-9A-Za-z])([0-9]{4})(?:[^0-9A-Za-z]|$)"), 9),
    # 5位纯数字
    (re.compile(r"(?:^|[^0-9A-Za-z])([0-9]{5})(?:[^0-9A-Za-z]|$)"), 9),
    # 6位字母数字
    (re.compile(r"(?:^|[^0-9A-Za-z])([A-Za-z0-9]{6})(?:[^0-9A-Za-z]|$)"), 8),
    # 7-8位数字
    (re.compile(r"(?:^|[^0-9A-Za-z])([0-9]{7,8})(?:[^0-9A-Za-z]|$)"), 7),
    # 4-8位字母数字
    (re.compile(r"(?:^|[^0-9A-Za-z])([A-Za-z0-9]{4,8})(?:[^0-9A-Za-z]|$)"), 6),
]


def extract_verification_code(text: str) -> Optional[str]:
    """智能提取验证码（4-8位数字/字母数字）。

    策略与前端 `extractVerificationCode` 基本对齐：
    - 关键词附近优先搜索
    - 全文扫描作为备选
    - 使用评分系统过滤金额、日期等噪声
    """
    if not text:
        return None

    candidates = []

    # 策略 1：在关键词附近查找（优先级最高）
    for pattern, kw_weight in _KEYWORDS:
        m = pattern.search(text)
        if not m:
            continue

        _, end = m.span()
        # 只搜索关键词之后的内容（避免误匹配前面的数字）
        search_range = text[end : min(len(text), end + 50)]

        for code_pattern, code_weight in _CODE_PATTERNS:
            m_code = code_pattern.search(search_range)
            if m_code and m_code.group(1):
                code = m_code.group(1)
                # 验证码必须包含至少一位数字，避免将普通英文单词（如 "review"）误判为验证码
                if not re.search(r"\d", code):
                    continue

                candidates.append(
                    {
                        "code": code,
                        "score": kw_weight + code_weight + 20,  # 关键词加成
                        "source": "keyword-context",
                    }
                )

    # 策略 2：全文查找（备选方案）
    if not candidates:
        for code_pattern, base_weight in _CODE_PATTERNS:
            for m in code_pattern.finditer(text):
                code = m.group(1)
                if not code:
                    continue

                # 验证码必须包含数字，过滤掉纯字母片段
                if not re.search(r"\d", code):
                    continue

                score = base_weight

                # 获取匹配位置的上下文
                start_index = m.start(1)
                end_index = m.end(1)
                before_context = text[max(0, start_index - 5) : start_index]
                after_context = text[end_index : min(len(text), end_index + 5)]

                # 惩罚：前面有货币符号（$, ¥, €, £）
                if re.search(r"[$¥€£]", before_context):
                    score -= 8

                # 惩罚：前后有小数点（金额）
                if "." in before_context or "." in after_context:
                    score -= 6

                # 惩罚：看起来像日期（2024, 2023 等）
                if re.fullmatch(r"20[0-9]{2}", code):
                    score -= 5

                # 惩罚：看起来像时间（1200, 1530 等）
                if re.fullmatch(r"[0-2][0-9][0-5][0-9]", code):
                    score -= 3

                # 惩罚：全是相同数字（1111, 0000）
                if re.fullmatch(r"(.)\1+", code):
                    score -= 4

                # 奖励：包含字母和数字混合（更可能是验证码）
                if re.search(r"[A-Za-z]", code) and re.search(r"[0-9]", code):
                    score += 3

                if score > 0:
                    candidates.append(
                        {
                            "code": code,
                            "score": score,
                            "source": "full-text",
                        }
                    )

    if not candidates:
        return None

    # 过滤掉明显是年份的候选（例如 2024），降低误报概率
    filtered = [
        c for c in candidates if not re.fullmatch(r"20[0-9]{2}", c["code"])
    ]
    if not filtered:
        return None

    filtered.sort(key=lambda c: c["score"], reverse=True)
    return filtered[0]["code"]


def extract_code_from_message(message: Dict[str, Any]) -> Optional[str]:
    """从邮件消息对象中提取验证码。

    - 自动处理 HTML / 纯文本
    - 优先使用 body.content，其次 bodyPreview
    """
    if not message:
        return None

    body = message.get("body") or {}
    body_content = body.get("content") or ""
    body_preview = message.get("bodyPreview") or ""

    text = body_content or body_preview or ""

    # 简单判断是否为 HTML
    content_type = (body.get("contentType") or "").lower()
    if content_type == "html" or re.search(r"<[^>]+>", text):
        text = _clean_html(text)

    return extract_verification_code(text)


__all__ = [
    "extract_verification_code",
    "extract_code_from_message",
]


