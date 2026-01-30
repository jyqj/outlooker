import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";
import type { Email } from "@/types";

export function cn(...inputs: ClassValue[]): string {
  return twMerge(clsx(inputs));
}

/**
 * 深度清理 HTML 内容，转换为纯文本
 */
function cleanHtml(html: string): string {
  let text = html;

  // 1. 移除 script 和 style 标签及其内容
  text = text.replace(/<script\b[^<]*(?:(?!<\/script>)<[^<]*)*<\/script>/gi, ' ');
  text = text.replace(/<style\b[^<]*(?:(?!<\/style>)<[^<]*)*<\/style>/gi, ' ');

  // 2. 移除所有 HTML 标签
  text = text.replace(/<[^>]+>/g, ' ');

  // 3. 解码常见 HTML 实体
  const entities: Record<string, string> = {
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
  text = text.replace(/&#(\d+);/g, (_match, dec) => String.fromCharCode(Number(dec)));
  text = text.replace(/&#x([0-9a-f]+);/gi, (_match, hex) => String.fromCharCode(parseInt(hex, 16)));

  // 5. 规范化空白字符
  text = text.replace(/\s+/g, ' ').trim();

  return text;
}

interface KeywordPattern {
  pattern: RegExp;
  weight: number;
}

interface CodePattern {
  pattern: RegExp;
  weight: number;
}

interface CodeCandidate {
  code: string;
  score: number;
  source: string;
}

/**
 * 智能提取验证码
 * 使用多层匹配策略和评分系统，支持中英文场景
 */
export function extractVerificationCode(text: string): string | null {
  if (!text) return null;

  // 验证码关键词（中英文）
  const keywords: KeywordPattern[] = [
    // 英文关键词
    { pattern: /(?:verification|verify|security|confirmation|auth(?:entication)?)\s*code/i, weight: 10 },
    { pattern: /\b(?:otp|pin|passcode|token)\b/i, weight: 9 },
    { pattern: /\bcode\b/i, weight: 7 },
    // 中文关键词
    { pattern: /验证码|校验码|动态码|安全码|确认码/i, weight: 10 },
  ];

  // 验证码模式（按优先级排序）
  const codePatterns: CodePattern[] = [
    { pattern: /(?:^|[^0-9A-Za-z])([0-9]{6})(?:[^0-9A-Za-z]|$)/, weight: 10 }, // 6位纯数字（最常见）
    { pattern: /(?:^|[^0-9A-Za-z])([0-9]{4})(?:[^0-9A-Za-z]|$)/, weight: 9 },  // 4位纯数字
    { pattern: /(?:^|[^0-9A-Za-z])([0-9]{5})(?:[^0-9A-Za-z]|$)/, weight: 9 },  // 5位纯数字
    { pattern: /(?:^|[^0-9A-Za-z])([A-Za-z0-9]{6})(?:[^0-9A-Za-z]|$)/i, weight: 8 }, // 6位字母数字
    { pattern: /(?:^|[^0-9A-Za-z])([0-9]{7,8})(?:[^0-9A-Za-z]|$)/, weight: 7 }, // 7-8位数字
    { pattern: /(?:^|[^0-9A-Za-z])([A-Za-z0-9]{4,8})(?:[^0-9A-Za-z]|$)/i, weight: 6 }, // 4-8位字母数字
  ];

  const candidates: CodeCandidate[] = [];

  // 策略 1：在关键词附近查找（优先级最高）
  for (const keyword of keywords) {
    const keywordMatch = text.match(keyword.pattern);
    if (keywordMatch && keywordMatch.index !== undefined) {
      const keywordEnd = keywordMatch.index + keywordMatch[0].length;
      // 只搜索关键词之后的内容（避免误匹配前面的数字）
      const searchRange = text.substring(
        keywordEnd,
        Math.min(text.length, keywordEnd + 50)
      );

      for (const codePattern of codePatterns) {
        const match = searchRange.match(codePattern.pattern);
        if (match && match[1]) {
          const code = match[1];
          // 验证码必须包含至少一位数字
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

          // 验证码必须包含数字
          if (!/\d/.test(code)) continue;

          let score = codePattern.weight;

          // 获取匹配位置的上下文
          const matchIndex = (match.index ?? 0) + (match[0].indexOf(code));
          const beforeContext = text.substring(Math.max(0, matchIndex - 5), matchIndex);
          const afterContext = text.substring(matchIndex + code.length, Math.min(text.length, matchIndex + code.length + 5));

          // 惩罚：前面有货币符号
          if (/[$¥€£]/.test(beforeContext)) score -= 8;

          // 惩罚：前后有小数点（金额）
          if (/\./.test(beforeContext) || /\./.test(afterContext)) score -= 6;

          // 惩罚：看起来像日期
          if (/^20[0-9]{2}$/.test(code)) score -= 5;

          // 惩罚：看起来像时间
          if (/^[0-2][0-9][0-5][0-9]$/.test(code)) score -= 3;

          // 惩罚：全是相同数字
          if (/^(.)\1+$/.test(code)) score -= 4;

          // 惩罚：全是字母
          if (/^[A-Za-z]+$/.test(code)) score -= 10;

          // 奖励：混合字母数字
          if (/[A-Za-z]/.test(code) && /[0-9]/.test(code)) score += 3;

          if (score > 0) {
            candidates.push({
              code,
              score,
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
 */
export function extractCodeFromMessage(message: Email | null | undefined): string | null {
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
  (typeof process !== "undefined" && process.env && process.env.NODE_ENV !== "production");

export function logError(message: string, error?: unknown): void {
  if (!isDevEnv || typeof console === "undefined") {
    return;
  }
  if (error) {
    console.error(`[Outlooker] ${message}`, error);
  } else {
    console.error(`[Outlooker] ${message}`);
  }
}

/**
 * 格式化日期时间为本地化字符串
 * @param dateString - ISO 日期字符串
 * @param options - Intl.DateTimeFormat 选项
 * @returns 格式化后的日期字符串
 */
export function formatDateTime(
  dateString: string,
  options?: Intl.DateTimeFormatOptions
): string {
  if (!dateString) return '未知';
  
  try {
    const date = new Date(dateString);
    if (isNaN(date.getTime())) return '未知';
    
    const defaultOptions: Intl.DateTimeFormatOptions = {
      year: 'numeric',
      month: 'long',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
    };
    
    return date.toLocaleString('zh-CN', options || defaultOptions);
  } catch {
    return '未知';
  }
}
