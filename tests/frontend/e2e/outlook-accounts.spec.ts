import { test, expect } from '@playwright/test';

async function loginAsAdmin(page) {
  await page.goto('/admin/login');
  await page.getByPlaceholder(/请输入用户名|Enter username/i).fill(process.env.TEST_ADMIN_USERNAME || 'admin');
  await page.getByPlaceholder(/请输入密码|Enter password/i).fill(process.env.TEST_ADMIN_PASSWORD || 'admin123');
  await page.click('button[type="submit"]');
  await page.waitForURL('/admin');
}

test.describe('Outlook Accounts Workbench', () => {
  test.beforeEach(async ({ page }) => {
    await loginAsAdmin(page);
  });

  test('should navigate to outlook accounts page', async ({ page }) => {
    await page.goto('/admin/outlook/accounts');
    await expect(page).toHaveURL(/\/admin\/outlook\/accounts/);
  });

  test('should open outlook account detail page', async ({ page }) => {
    await page.goto('/admin/outlook/accounts');
    const detailButton = page.getByRole('button', { name: /查看详情/i }).first();
    if (await detailButton.isVisible()) {
      await detailButton.click();
      await expect(page).toHaveURL(/\/admin\/outlook\/accounts\//);
    }
  });
});
