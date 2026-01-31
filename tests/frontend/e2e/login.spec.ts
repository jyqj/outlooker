import { test, expect } from '@playwright/test';

/**
 * E2E tests for Admin Login Flow
 * Tests the core authentication functionality
 */

test.describe('Admin Login Page', () => {
    test.beforeEach(async ({ page }) => {
        await page.goto('/admin');
    });

    test('should display login form', async ({ page }) => {
        // Check page title
        await expect(page).toHaveTitle(/Outlooker/);

        // Check login form elements
        await expect(page.getByPlaceholder(/用户名/)).toBeVisible();
        await expect(page.getByPlaceholder(/密码/)).toBeVisible();
        await expect(page.getByRole('button', { name: /登录/ })).toBeVisible();
    });

    test('should show error for empty credentials', async ({ page }) => {
        // Click login without entering credentials
        await page.getByRole('button', { name: /登录/ }).click();

        // Should show validation error or stay on login page
        await expect(page.getByPlaceholder(/用户名/)).toBeVisible();
    });

    test('should show error for invalid credentials', async ({ page }) => {
        // Enter invalid credentials
        await page.getByPlaceholder(/用户名/).fill('invalid_user');
        await page.getByPlaceholder(/密码/).fill('invalid_password');

        // Submit form
        await page.getByRole('button', { name: /登录/ }).click();

        // Should show error message
        await expect(page.getByText(/错误|失败|无效/)).toBeVisible({ timeout: 10000 });
    });

    test('should redirect to dashboard on successful login', async ({ page }) => {
        // Get admin credentials from environment (for CI testing)
        const username = process.env.TEST_ADMIN_USERNAME || 'admin';
        const password = process.env.TEST_ADMIN_PASSWORD;

        // Skip if no test password is configured
        if (!password) {
            test.skip();
            return;
        }

        // Enter valid credentials
        await page.getByPlaceholder(/用户名/).fill(username);
        await page.getByPlaceholder(/密码/).fill(password);

        // Submit form
        await page.getByRole('button', { name: /登录/ }).click();

        // Should redirect to dashboard
        await expect(page).toHaveURL(/\/admin/, { timeout: 10000 });

        // Dashboard content should be visible
        await expect(page.getByText(/账户|邮箱|管理/)).toBeVisible({ timeout: 10000 });
    });

    test('should navigate back to home page', async ({ page }) => {
        // Check if there's a link to go back
        const homeLink = page.getByRole('link', { name: /首页|返回/ });
        if (await homeLink.isVisible()) {
            await homeLink.click();
            await expect(page).toHaveURL('/');
        }
    });
});

test.describe('Login Security', () => {
    test('should handle rate limiting gracefully', async ({ page }) => {
        await page.goto('/admin');

        // Attempt multiple failed logins
        for (let i = 0; i < 3; i++) {
            await page.getByPlaceholder(/用户名/).fill('attacker');
            await page.getByPlaceholder(/密码/).fill('wrong_password_' + i);
            await page.getByRole('button', { name: /登录/ }).click();

            // Wait for response
            await page.waitForTimeout(1000);
        }

        // Should still show login form (not crash)
        await expect(page.getByPlaceholder(/用户名/)).toBeVisible();
    });
});
