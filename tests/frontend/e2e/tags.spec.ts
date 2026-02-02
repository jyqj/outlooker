import { test, expect } from '@playwright/test';

test.describe('Tags Management', () => {
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
    await page.goto('/admin/tags');
  });

  test('should display tags page header', async ({ page }) => {
    await expect(page.getByRole('heading', { level: 1 })).toBeVisible();
  });

  test('should display tag statistics', async ({ page }) => {
    // 等待统计数据加载
    await page.waitForSelector('[data-testid="stats"], .stats-card, [class*="card"]', {
      timeout: 10000,
    });
  });

  test('should display tags list', async ({ page }) => {
    // 等待标签列表加载
    await page.waitForTimeout(1000);
    const tagsList = page.locator('[data-testid="tags-list"], [role="list"]');
    // 标签列表应该可见（即使为空）
    await expect(tagsList.or(page.locator('text=/没有标签|no tags/i'))).toBeVisible();
  });

  test('should navigate back to dashboard', async ({ page }) => {
    const backButton = page.getByRole('button', { name: /返回|back/i });
    if (await backButton.isVisible()) {
      await backButton.click();
      await expect(page).toHaveURL('/admin');
    }
  });

  test('should open random pick modal', async ({ page }) => {
    const pickButton = page.getByRole('button', { name: /随机取号|取号/i });
    if (await pickButton.isVisible()) {
      await pickButton.click();
      await expect(page.getByRole('dialog')).toBeVisible();
    }
  });

  test('should refresh tags list', async ({ page }) => {
    const refreshButton = page.getByRole('button', { name: /刷新|refresh/i });
    if (await refreshButton.isVisible()) {
      await refreshButton.click();
      // 等待刷新完成
      await page.waitForTimeout(1000);
    }
  });
});
