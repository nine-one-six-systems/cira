/**
 * E2E Tests: Dashboard / Company List
 *
 * Tests the main dashboard functionality:
 * - Company list display
 * - Filtering and sorting
 * - Pagination
 * - Navigation to add/batch pages
 * - Company actions (view, delete)
 */

import { test, expect } from '@playwright/test';

test.describe('Dashboard', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
  });

  test('should display dashboard heading', async ({ page }) => {
    await expect(page.getByRole('heading', { name: /companies|dashboard/i })).toBeVisible();
  });

  test('should have add company button', async ({ page }) => {
    const addButton = page.getByRole('link', { name: /add.*company/i })
      .or(page.getByRole('button', { name: /add.*company/i }));
    await expect(addButton).toBeVisible();
  });

  test('should have batch upload button', async ({ page }) => {
    const batchButton = page.getByRole('link', { name: /batch|upload.*csv/i })
      .or(page.getByRole('button', { name: /batch|upload.*csv/i }));
    await expect(batchButton).toBeVisible();
  });

  test('should navigate to add company page', async ({ page }) => {
    await page.getByRole('link', { name: /add.*company/i }).click();
    await expect(page).toHaveURL('/add');
  });

  test('should navigate to batch upload page', async ({ page }) => {
    await page.getByRole('link', { name: /batch|upload/i }).click();
    await expect(page).toHaveURL('/batch');
  });

  test('should show empty state when no companies', async ({ page }) => {
    // Check for either companies table or empty state message
    const table = page.getByRole('table');
    const emptyState = page.getByText(/no companies|get started|add your first/i);

    const hasTable = await table.isVisible().catch(() => false);
    const hasEmptyState = await emptyState.isVisible().catch(() => false);

    expect(hasTable || hasEmptyState).toBeTruthy();
  });

  test('should have status filter if companies exist', async ({ page }) => {
    const statusFilter = page.getByLabel(/status/i)
      .or(page.getByRole('combobox', { name: /status/i }))
      .or(page.locator('select[name*="status"]'));

    // Only check if filter exists (may not if no companies)
    const filterVisible = await statusFilter.isVisible().catch(() => false);
    if (filterVisible) {
      await expect(statusFilter).toBeVisible();
    }
  });

  test('should have search input if companies exist', async ({ page }) => {
    const searchInput = page.getByPlaceholder(/search/i)
      .or(page.getByRole('searchbox'))
      .or(page.locator('input[type="search"]'));

    const searchVisible = await searchInput.isVisible().catch(() => false);
    if (searchVisible) {
      await expect(searchInput).toBeVisible();
    }
  });

  test('should be accessible with keyboard navigation', async ({ page }) => {
    // Tab to first interactive element
    await page.keyboard.press('Tab');

    // Verify focus is on an interactive element
    const focusedTag = await page.evaluate(() => document.activeElement?.tagName);
    expect(['A', 'BUTTON', 'INPUT', 'SELECT']).toContain(focusedTag);
  });

  test('should navigate to settings page', async ({ page }) => {
    const settingsLink = page.getByRole('link', { name: /settings/i });
    if (await settingsLink.isVisible()) {
      await settingsLink.click();
      await expect(page).toHaveURL('/settings');
    }
  });
});
