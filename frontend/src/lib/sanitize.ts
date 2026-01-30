/**
 * HTML sanitization utilities
 */

import createDOMPurify from 'dompurify';

let purifier: ReturnType<typeof createDOMPurify> | null = null;

function getPurifier(): ReturnType<typeof createDOMPurify> | null {
  if (purifier) return purifier;
  if (typeof window === 'undefined') return null;
  purifier = createDOMPurify(window);
  return purifier;
}

export function sanitizeHtml(rawHtml: string = ''): string {
  if (!rawHtml || typeof rawHtml !== 'string') {
    return '';
  }

  const domPurify = getPurifier();
  // SSR/纯 Node 环境：保持兼容性（不在浏览器执行脚本）
  if (!domPurify || !domPurify.isSupported) {
    return rawHtml.replace(/<script[\s\S]*?>[\s\S]*?<\/script>/gi, '');
  }

  return String(
    domPurify.sanitize(rawHtml, {
      USE_PROFILES: { html: true },
      FORBID_TAGS: ['script', 'style', 'iframe', 'object', 'embed', 'link', 'meta', 'svg', 'math'],
      FORBID_ATTR: ['style'],
    })
  );
}
