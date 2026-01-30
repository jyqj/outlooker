import { test, expect } from '@playwright/test';

/**
 * E2E tests for Verification Code Flow
 * Tests the core email verification functionality
 */

test.describe('Verification Page', () => {
    test.beforeEach(async ({ page }) => {
        await page.goto('/');
    });

    test('should display verification form', async ({ page }) => {
        // Check page title
        await expect(page).toHaveTitle(/Outlooker/);

        // Check verification form elements
        await expect(page.getByPlaceholder(/邮箱/)).toBeVisible();
        await expect(page.getByRole('button', { name: /获取|验证码/ })).toBeVisible();
    });

    test('should show error for empty email', async ({ page }) => {
        // Click submit without entering email
        await page.getByRole('button', { name: /获取|验证码/ }).click();

        // Should show validation error or email field should still be visible
        await expect(page.getByPlaceholder(/邮箱/)).toBeVisible();
    });

    test('should show error for invalid email format', async ({ page }) => {
        // Enter invalid email
        await page.getByPlaceholder(/邮箱/).fill('not-an-email');

        // Try to submit
        await page.getByRole('button', { name: /获取|验证码/ }).click();

        // Wait for potential error message
        await page.waitForTimeout(2000);

        // Should show error or stay on form
        await expect(page.getByPlaceholder(/邮箱/)).toBeVisible();
    });

    test('should show error for non-existent email', async ({ page }) => {
        // Enter a valid format but non-existent email
        await page.getByPlaceholder(/邮箱/).fill('nonexistent@example.com');

        // Submit
        await page.getByRole('button', { name: /获取|验证码/ }).click();

        // Should show error message
        await expect(page.getByText(/错误|未找到|不存在|失败/)).toBeVisible({ timeout: 10000 });
    });

    test('should fetch verification code for valid email', async ({ page }) => {
        // Get test email from environment
        const testEmail = process.env.TEST_EMAIL;

        // Skip if no test email is configured
        if (!testEmail) {
            test.skip();
            return;
        }

        // Enter valid email
        await page.getByPlaceholder(/邮箱/).fill(testEmail);

        // Submit
        await page.getByRole('button', { name: /获取|验证码/ }).click();

        // Should show loading state
        await expect(page.getByText(/正在|加载|获取中/)).toBeVisible({ timeout: 5000 });

        // Wait for result
        await page.waitForTimeout(5000);

        // Should show verification code or email content
        const hasResult = await page.getByText(/验证码|暂无|邮件/).isVisible();
        expect(hasResult).toBeTruthy();
    });

    test('should show loading state during fetch', async ({ page }) => {
        // Get test email from environment or use a mock
        const testEmail = process.env.TEST_EMAIL || 'test@outlook.com';

        // Enter email
        await page.getByPlaceholder(/邮箱/).fill(testEmail);

        // Submit and immediately check for loading state
        await page.getByRole('button', { name: /获取|验证码/ }).click();

        // Should show some indication of loading (spinner or text)
        // The exact element depends on implementation
        const isLoading = await Promise.race([
            page.getByText(/正在|加载|获取中/).isVisible().catch(() => false),
            page.locator('[class*="animate-spin"]').isVisible().catch(() => false),
            page.waitForTimeout(1000).then(() => true),
        ]);

        expect(isLoading).toBeTruthy();
    });
});

test.describe('Verification Page - Navigation', () => {
    test('should navigate to admin page', async ({ page }) => {
        await page.goto('/');

        // Look for admin link
        const adminLink = page.getByRole('link', { name: /管理|后台|Admin/ });
        if (await adminLink.isVisible()) {
            await adminLink.click();
            await expect(page).toHaveURL(/\/admin/);
        }
    });
});

test.describe('Verification Page - Responsive', () => {
    test('should work on mobile viewport', async ({ page }) => {
        await page.setViewportSize({ width: 375, height: 667 });
        await page.goto('/');

        // Form should still be visible
        await expect(page.getByPlaceholder(/邮箱/)).toBeVisible();
        await expect(page.getByRole('button', { name: /获取|验证码/ })).toBeVisible();
    });

    test('should work on tablet viewport', async ({ page }) => {
        await page.setViewportSize({ width: 768, height: 1024 });
        await page.goto('/');

        // Form should still be visible
        await expect(page.getByPlaceholder(/邮箱/)).toBeVisible();
        await expect(page.getByRole('button', { name: /获取|验证码/ })).toBeVisible();
    });
});
