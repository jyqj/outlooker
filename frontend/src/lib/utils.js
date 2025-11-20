import { clsx } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs) {
  return twMerge(clsx(inputs));
}

export function extractVerificationCode(text) {
  // 常见验证码模式
  const patterns = [
    /\b\d{4,6}\b/, // 4-6位数字
    /\b[A-Z0-9]{4,8}\b/, // 4-8位大写字母+数字
  ];

  for (const pattern of patterns) {
    const match = text.match(pattern);
    if (match) {
      return match[0];
    }
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
  
  const bodyText = message.body?.content || message.bodyPreview || '';
  // 去除 HTML 标签，替换为空格以保持单词边界
  const plainText = bodyText.replace(/<[^>]*>/g, ' ');
  return extractVerificationCode(plainText);
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
