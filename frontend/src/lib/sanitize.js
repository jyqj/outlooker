export function sanitizeHtml(rawHtml = '') {
  if (!rawHtml || typeof rawHtml !== 'string') {
    return '';
  }

  // 服务器端渲染或测试环境没有 DOM Parser，退回到简单过滤
  if (typeof window === 'undefined' || typeof DOMParser === 'undefined') {
    return rawHtml.replace(/<script[\s\S]*?>[\s\S]*?<\/script>/gi, '');
  }

  const parser = new DOMParser();
  const doc = parser.parseFromString(rawHtml, 'text/html');

  const blockedSelectors = ['script', 'style', 'iframe', 'object', 'embed', 'link', 'meta'];
  doc.querySelectorAll(blockedSelectors.join(',')).forEach((node) => node.remove());

  const walker = document.createTreeWalker(doc.body, NodeFilter.SHOW_ELEMENT);
  while (walker.nextNode()) {
    const node = walker.currentNode;
    // 移除 on* 属性和 javascript: 协议
    [...node.attributes].forEach((attr) => {
      const name = attr.name.toLowerCase();
      const value = String(attr.value || '').toLowerCase();
      if (name.startsWith('on') || value.startsWith('javascript:')) {
        node.removeAttribute(attr.name);
      }
    });
  }

  return doc.body.innerHTML;
}
