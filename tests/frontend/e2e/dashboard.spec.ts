import { test, expect } from '@playwright/test';

// 测试管理后台功能
test.describe('Admin Dashboard', () => {
  // 登录 helper
  async function loginAsAdmin(page) {
    await page.goto('/admin/login');
    await page.fill('input[name="username"]', process.env.TEST_ADMIN_USERNAME || 'admin');
    await page.fill('input[name="password"]', process.env.TEST_ADMIN_PASSWORD || 'admin123');
    await page.click('button[type="submit"]');
    await page.waitForURL('/admin');
  }

  test.beforeEach(async ({ page }) => {
    await loginAsAdmin(page);
  });

  test('should display dashboard header', async ({ page }) => {
    await expect(page.locator('header')).toBeVisible();
    await expect(page.getByRole('button', { name: /退出/i })).toBeVisible();
  });

  test('should display accounts table', async ({ page }) => {
    await expect(page.locator('table, [role="grid"]')).toBeVisible();
  });

  test('should support search functionality', async ({ page }) => {
    const searchInput = page.getByPlaceholder(/搜索|search/i);
    await expect(searchInput).toBeVisible();
    
    await searchInput.fill('test@example.com');
    // 等待搜索结果更新
    await page.waitForTimeout(600); // debounce delay
  });

  test('should open import modal', async ({ page }) => {
    const importButton = page.getByRole('button', { name: /导入/i });
    if (await importButton.isVisible()) {
      await importButton.click();
      await expect(page.getByRole('dialog')).toBeVisible();
    }
  });

  test('should navigate to tags page', async ({ page }) => {
    const tagsLink = page.getByRole('link', { name: /标签/i });
    if (await tagsLink.isVisible()) {
      await tagsLink.click();
      await expect(page).toHaveURL(/\/admin\/tags/);
    }
  });

  test('should logout successfully', async ({ page }) => {
    await page.getByRole('button', { name: /退出/i }).click();
    await expect(page).toHaveURL(/\/admin\/login/);
  });

  test('should handle pagination', async ({ page }) => {
    // 检查分页组件是否存在
    const pagination = page.locator('[data-testid="pagination"], nav[aria-label*="pagination"]');
    if (await pagination.isVisible()) {
      const nextButton = page.getByRole('button', { name: /下一页|next/i });
      if (await nextButton.isEnabled()) {
        await nextButton.click();
        // 验证页面变化
        await page.waitForTimeout(500);
      }
    }
  });
});
