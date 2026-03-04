/**
 * 标签校验规则常量和校验函数
 * 前后端共享相同的校验规则
 */

export const TAG_RULES = {
  MAX_LENGTH: 20,
  MAX_COUNT: 10,
  INVALID_CHARS: /[<>&"']/,
} as const;

/**
 * 校验单个标签
 * @param tag 标签字符串
 * @param existingTags 已存在的标签列表（用于检查重复和数量限制）
 * @returns 错误信息，如果校验通过则返回 null
 */
export function validateTag(tag: string, existingTags: string[]): string | null {
  if (!tag) {
    return '标签不能为空';
  }
  if (tag.length > TAG_RULES.MAX_LENGTH) {
    return `标签长度不能超过 ${TAG_RULES.MAX_LENGTH} 个字符`;
  }
  if (TAG_RULES.INVALID_CHARS.test(tag)) {
    return '标签不能包含特殊字符 < > & " \'';
  }
  if (existingTags.includes(tag)) {
    return '该标签已存在';
  }
  if (existingTags.length >= TAG_RULES.MAX_COUNT) {
    return `最多只能添加 ${TAG_RULES.MAX_COUNT} 个标签`;
  }
  return null;
}

/**
 * 校验批量标签字符串
 * @param tagsString 逗号分隔的标签字符串
 * @returns 错误信息，如果校验通过则返回 null
 */
export function validateBatchTags(tagsString: string): string | null {
  if (!tagsString.trim() && tagsString !== '') {
    return null; // 允许空字符串（用于 set 模式清空标签）
  }
  
  const tags = tagsString.split(',').map(t => t.trim()).filter(Boolean);
  
  if (tags.length === 0) {
    return null; // 空标签列表在某些模式下是允许的
  }
  
  for (const tag of tags) {
    if (tag.length > TAG_RULES.MAX_LENGTH) {
      return `标签 "${tag}" 长度超过 ${TAG_RULES.MAX_LENGTH} 个字符`;
    }
    if (TAG_RULES.INVALID_CHARS.test(tag)) {
      return `标签 "${tag}" 包含特殊字符 < > & " '`;
    }
  }
  
  return null;
}
