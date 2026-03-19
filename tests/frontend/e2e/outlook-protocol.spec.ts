import { test, expect } from '@playwright/test';

async function loginAsAdmin(page) {
  await page.goto('/admin/login');
  await page.getByPlaceholder(/请输入用户名|Enter username/i).fill(process.env.TEST_ADMIN_USERNAME || 'admin');
  await page.getByPlaceholder(/请输入密码|Enter password/i).fill(process.env.TEST_ADMIN_PASSWORD || 'admin123');
  await page.click('button[type="submit"]');
  await page.waitForURL('/admin');
}

test.describe('Outlook Protocol Wizard', () => {
  test.beforeEach(async ({ page }) => {
    await loginAsAdmin(page);
  });

  test('should open protocol wizard from tasks page', async ({ page }) => {
    await page.goto('/admin/outlook/tasks');
    await expect(page.getByText(/协议绑定向导/)).toBeVisible();
    await expect(page.getByRole('button', { name: /test-login/i })).toBeVisible();
  });
});
