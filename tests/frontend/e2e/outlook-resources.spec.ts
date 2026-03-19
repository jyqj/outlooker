import { test, expect } from '@playwright/test';

async function loginAsAdmin(page) {
  await page.goto('/admin/login');
  await page.getByPlaceholder(/请输入用户名|Enter username/i).fill(process.env.TEST_ADMIN_USERNAME || 'admin');
  await page.getByPlaceholder(/请输入密码|Enter password/i).fill(process.env.TEST_ADMIN_PASSWORD || 'admin123');
  await page.click('button[type="submit"]');
  await page.waitForURL('/admin');
}

test.describe('Aux Email Pool', () => {
  test.beforeEach(async ({ page }) => {
    await loginAsAdmin(page);
  });

  test('should open resources page', async ({ page }) => {
    await page.goto('/admin/outlook/resources');
    await expect(page.getByText(/辅助邮箱资源池/)).toBeVisible();
  });
});
