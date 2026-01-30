import { describe, it, expect, vi } from 'vitest';

import { sanitizeHtml } from '../sanitize';

describe('sanitizeHtml', () => {
  it('removes <script> blocks', () => {
    const dirty = '<div>Hello<script>alert(1)</script><p>World</p></div>';
    const clean = sanitizeHtml(dirty);
    expect(clean).toContain('Hello');
    expect(clean).toContain('World');
    expect(clean).not.toContain('<script');
    expect(clean).not.toContain('alert(1)');
  });

  it('removes event handler attributes', () => {
    const dirty = '<img src="x" onerror="alert(1)" />';
    const clean = sanitizeHtml(dirty);
    expect(clean).toContain('<img');
    expect(clean.toLowerCase()).not.toContain('onerror');
  });

  it('removes javascript: URLs', () => {
    const dirty = '<a href="javascript:alert(1)">x</a>';
    const clean = sanitizeHtml(dirty);
    expect(clean).toContain('<a');
    expect(clean.toLowerCase()).not.toContain('javascript:');
  });

  it('removes svg/math content to reduce XSS surface', () => {
    const dirty = '<svg><g onload="alert(1)"></g></svg><p>ok</p><math></math>';
    const clean = sanitizeHtml(dirty);
    expect(clean).toContain('ok');
    expect(clean.toLowerCase()).not.toContain('<svg');
    expect(clean.toLowerCase()).not.toContain('<math');
  });

  it('falls back gracefully when window is unavailable (SSR)', async () => {
    vi.stubGlobal('window', undefined);
    vi.resetModules();

    const { sanitizeHtml: sanitizeHtmlSsr } = await import('../sanitize');
    const dirty = '<b>ok</b><script>alert(1)</script>';
    const clean = sanitizeHtmlSsr(dirty);

    expect(clean).toContain('<b>ok</b>');
    expect(clean.toLowerCase()).not.toContain('<script');

    vi.unstubAllGlobals();
  });
});

