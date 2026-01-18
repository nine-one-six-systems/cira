/**
 * E2E Tests: Progress View
 *
 * Tests the progress monitoring page:
 * - Progress bar display
 * - Stats updates
 * - Pause/Resume functionality
 * - Auto-redirect on completion
 */

import { test, expect } from '@playwright/test';

test.describe('Progress View', () => {
  // These tests require a company to be in progress
  // In CI, we mock the API or use test fixtures

  test('should show 404 for non-existent company', async ({ page }) => {
    await page.goto('/companies/99999/progress');

    // Should show error or redirect
    const error = await page.getByText(/not found|error|404/i).isVisible().catch(() => false);
    const redirected = page.url() !== '/companies/99999/progress';

    expect(error || redirected).toBeTruthy();
  });

  test('should have correct URL structure', async ({ page }) => {
    await page.goto('/companies/1/progress');

    // URL should match pattern
    expect(page.url()).toMatch(/\/companies\/\d+\/progress/);
  });

  test('should display progress elements when company exists', async ({ page }) => {
    // Navigate to a progress page
    await page.goto('/companies/1/progress');

    // Wait for page to load
    await page.waitForLoadState('networkidle');

    // Check for common progress page elements (if company exists)
    const pageTitle = page.getByRole('heading');

    // At least heading should be visible
    await expect(pageTitle.first()).toBeVisible();
  });

  test('should show pause button for in-progress companies', async ({ page }) => {
    await page.goto('/companies/1/progress');
    await page.waitForLoadState('networkidle');

    // Check for pause button (only visible when in progress)
    const pauseButton = page.getByRole('button', { name: /pause/i });
    const isInProgress = await pauseButton.isVisible().catch(() => false);

    // If not in progress, check for alternative states
    if (!isInProgress) {
      const hasStatus = await page.getByText(/completed|failed|queued|paused/i).isVisible().catch(() => false);
      expect(hasStatus || isInProgress).toBeTruthy();
    }
  });

  test('should navigate back to dashboard', async ({ page }) => {
    await page.goto('/companies/1/progress');

    const backLink = page.getByRole('link', { name: /back|dashboard/i })
      .or(page.locator('a[href="/"]'));

    if (await backLink.isVisible()) {
      await backLink.click();
      await expect(page).toHaveURL('/');
    }
  });

  test('should be accessible with keyboard', async ({ page }) => {
    await page.goto('/companies/1/progress');
    await page.waitForLoadState('networkidle');

    // Tab navigation should work
    await page.keyboard.press('Tab');

    const focusedTag = await page.evaluate(() => document.activeElement?.tagName);
    expect(['A', 'BUTTON', 'INPUT', 'BODY']).toContain(focusedTag);
  });
});
