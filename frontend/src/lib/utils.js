import { clsx } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs) {
  return twMerge(clsx(inputs));
}

/**
 * 深度清理 HTML 内容，转换为纯文本
 * @param {string} html - HTML 字符串
 * @returns {string} 清理后的纯文本
 */
function cleanHtml(html) {
  let text = html;

  // 1. 移除 script 和 style 标签及其内容
  text = text.replace(/<script\b[^<]*(?:(?!<\/script>)<[^<]*)*<\/script>/gi, ' ');
  text = text.replace(/<style\b[^<]*(?:(?!<\/style>)<[^<]*)*<\/style>/gi, ' ');

  // 2. 移除所有 HTML 标签
  text = text.replace(/<[^>]+>/g, ' ');

  // 3. 解码常见 HTML 实体
  const entities = {
    '&nbsp;': ' ',
    '&lt;': '<',
    '&gt;': '>',
    '&amp;': '&',
    '&quot;': '"',
    '&#39;': "'",
    '&apos;': "'"
  };

  for (const [entity, char] of Object.entries(entities)) {
    text = text.replace(new RegExp(entity, 'g'), char);
  }

  // 4. 解码数字实体
  text = text.replace(/&#(\d+);/g, (match, dec) => String.fromCharCode(dec));
  text = text.replace(/&#x([0-9a-f]+);/gi, (match, hex) => String.fromCharCode(parseInt(hex, 16)));

  // 5. 规范化空白字符
  text = text.replace(/\s+/g, ' ').trim();

  return text;
}

/**
 * 智能提取验证码
 * 使用多层匹配策略和评分系统，支持中英文场景
 * @param {string} text - 要提取验证码的文本
 * @returns {string|null} 提取的验证码，未找到则返回 null
 */
export function extractVerificationCode(text) {
  if (!text) return null;

  // 验证码关键词（中英文）
  const keywords = [
    // 英文关键词
    { pattern: /(?:verification|verify|security|confirmation|auth(?:entication)?)\s*code/i, weight: 10 },
    { pattern: /\b(?:otp|pin|passcode|token)\b/i, weight: 9 },
    { pattern: /\bcode\b/i, weight: 7 },
    // 中文关键词
    { pattern: /验证码|校验码|动态码|安全码|确认码/i, weight: 10 },
  ];

  // 验证码模式（按优先级排序）
  const codePatterns = [
    { pattern: /(?:^|[^0-9A-Za-z])([0-9]{6})(?:[^0-9A-Za-z]|$)/, weight: 10 }, // 6位纯数字（最常见）
    { pattern: /(?:^|[^0-9A-Za-z])([0-9]{4})(?:[^0-9A-Za-z]|$)/, weight: 9 },  // 4位纯数字
    { pattern: /(?:^|[^0-9A-Za-z])([0-9]{5})(?:[^0-9A-Za-z]|$)/, weight: 9 },  // 5位纯数字
    { pattern: /(?:^|[^0-9A-Za-z])([A-Za-z0-9]{6})(?:[^0-9A-Za-z]|$)/i, weight: 8 }, // 6位字母数字
    { pattern: /(?:^|[^0-9A-Za-z])([0-9]{7,8})(?:[^0-9A-Za-z]|$)/, weight: 7 }, // 7-8位数字
    { pattern: /(?:^|[^0-9A-Za-z])([A-Za-z0-9]{4,8})(?:[^0-9A-Za-z]|$)/i, weight: 6 }, // 4-8位字母数字
  ];

  const candidates = [];

  // 策略 1：在关键词附近查找（优先级最高）
  for (const keyword of keywords) {
    const keywordMatch = text.match(keyword.pattern);
    if (keywordMatch) {
      const keywordIndex = keywordMatch.index;
      const keywordEnd = keywordIndex + keywordMatch[0].length;
      // 只搜索关键词之后的内容（避免误匹配前面的数字）
      const searchRange = text.substring(
        keywordEnd,
        Math.min(text.length, keywordEnd + 50)
      );

      for (const codePattern of codePatterns) {
        const match = searchRange.match(codePattern.pattern);
        if (match && match[1]) {
          const code = match[1];
          // 验证码必须包含至少一位数字，避免将普通英文单词（如 "review"）误判为验证码
          if (!/\d/.test(code)) continue;

          candidates.push({
            code,
            score: keyword.weight + codePattern.weight + 20, // 关键词加成
            source: 'keyword-context'
          });
        }
      }
    }
  }

  // 策略 2：全文查找（备选方案）
  if (candidates.length === 0) {
    for (const codePattern of codePatterns) {
      const matches = text.matchAll(new RegExp(codePattern.pattern.source, 'g'));
      for (const match of matches) {
        if (match[1]) {
          const code = match[1];

          // 验证码必须包含数字，直接过滤掉纯字母片段
          if (!/\d/.test(code)) {
            continue;
          }

          // 降低日期和金额的权重
          let score = codePattern.weight;

          // 获取匹配位置的上下文
          const matchIndex = match.index + (match[0].indexOf(code));
          const beforeContext = text.substring(Math.max(0, matchIndex - 5), matchIndex);
          const afterContext = text.substring(matchIndex + code.length, Math.min(text.length, matchIndex + code.length + 5));

          // 惩罚：前面有货币符号（$, ¥, €, £）
          if (/[$¥€£]/.test(beforeContext)) score -= 8;

          // 惩罚：前后有小数点（金额）
          if (/\./.test(beforeContext) || /\./.test(afterContext)) score -= 6;

          // 惩罚：看起来像日期（2024, 2023 等）
          if (/^20[0-9]{2}$/.test(code)) score -= 5;

          // 惩罚：看起来像时间（1200, 1530 等）
          if (/^[0-2][0-9][0-5][0-9]$/.test(code)) score -= 3;

          // 惩罚：全是相同数字（1111, 0000）
          if (/^(.)\1+$/.test(code)) score -= 4;

          // 惩罚：全是字母（可能是单词片段）
          if (/^[A-Za-z]+$/.test(code)) score -= 10;

          // 奖励：包含字母和数字混合（更可能是验证码）
          if (/[A-Za-z]/.test(code) && /[0-9]/.test(code)) score += 3;

          // 只添加得分为正的候选项
          if (score > 0) {
            candidates.push({
              code: code,
              score: score,
              source: 'full-text'
            });
          }
        }
      }
    }
  }

  // 选择得分最高的候选项
  if (candidates.length > 0) {
    candidates.sort((a, b) => b.score - a.score);
    return candidates[0].code;
  }

  return null;
}

/**
 * 从邮件消息中提取验证码
 * 自动处理 HTML 标签去除和文本提取
 * @param {Object} message - 邮件消息对象
 * @returns {string|null} 提取的验证码，未找到则返回 null
 */
export function extractCodeFromMessage(message) {
  if (!message) return null;

  // 优先使用 body.content，其次 bodyPreview
  let bodyText = message.body?.content || message.bodyPreview || '';

  // 如果是 HTML，进行深度清理
  if (message.body?.contentType === 'html' || /<[^>]+>/.test(bodyText)) {
    bodyText = cleanHtml(bodyText);
  }

  return extractVerificationCode(bodyText);
}

const isDevEnv =
  (typeof import.meta !== "undefined" && import.meta.env && import.meta.env.DEV) ||
  // eslint-disable-next-line no-undef
  (typeof process !== "undefined" && process.env && process.env.NODE_ENV !== "production");

export function logError(message, error) {
  if (!isDevEnv || typeof console === "undefined") {
    return;
  }
  if (error) {
    console.error(`[Outlooker] ${message}`, error);
  } else {
    console.error(`[Outlooker] ${message}`);
  }
}
