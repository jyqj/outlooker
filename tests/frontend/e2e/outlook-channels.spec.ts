import { test, expect } from '@playwright/test';

async function loginAsAdmin(page) {
  await page.goto('/admin/login');
  await page.getByPlaceholder(/请输入用户名|Enter username/i).fill(process.env.TEST_ADMIN_USERNAME || 'admin');
  await page.getByPlaceholder(/请输入密码|Enter password/i).fill(process.env.TEST_ADMIN_PASSWORD || 'admin123');
  await page.click('button[type="submit"]');
  await page.waitForURL('/admin');
}

test.describe('Channel Console', () => {
  test.beforeEach(async ({ page }) => {
    await loginAsAdmin(page);
  });

  test('should open channels console', async ({ page }) => {
    await page.goto('/admin/outlook/channels');
    await expect(page.getByText(/渠道控制台/)).toBeVisible();
  });
});
