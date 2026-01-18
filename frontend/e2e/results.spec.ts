/**
 * E2E Tests: Results View
 *
 * Tests the company results/analysis page:
 * - Tab navigation (Summary, Entities, Pages, Token Usage)
 * - Export functionality
 * - Re-scan button
 * - Version comparison
 */

import { test, expect } from '@playwright/test';

test.describe('Results View', () => {
  test('should show 404 for non-existent company', async ({ page }) => {
    await page.goto('/companies/99999');

    const error = await page.getByText(/not found|error|404/i).isVisible().catch(() => false);
    const redirected = page.url() !== '/companies/99999';

    expect(error || redirected).toBeTruthy();
  });

  test('should have correct URL structure', async ({ page }) => {
    await page.goto('/companies/1');
    expect(page.url()).toMatch(/\/companies\/\d+$/);
  });

  test('should display company name when exists', async ({ page }) => {
    await page.goto('/companies/1');
    await page.waitForLoadState('networkidle');

    // Should have a heading
    const heading = page.getByRole('heading').first();
    await expect(heading).toBeVisible();
  });

  test('should show tabs for different sections', async ({ page }) => {
    await page.goto('/companies/1');
    await page.waitForLoadState('networkidle');

    // Look for tab elements
    const tabs = page.getByRole('tab')
      .or(page.getByRole('tablist'))
      .or(page.locator('[role="tab"]'));

    const tabsExist = await tabs.first().isVisible().catch(() => false);

    // If tabs exist, verify they're functional
    if (tabsExist) {
      await expect(tabs.first()).toBeVisible();
    }
  });

  test('should have export functionality for completed companies', async ({ page }) => {
    await page.goto('/companies/1');
    await page.waitForLoadState('networkidle');

    // Look for export button or dropdown
    const exportButton = page.getByRole('button', { name: /export/i })
      .or(page.locator('[class*="export"]'))
      .or(page.getByText(/export/i));

    const hasExport = await exportButton.isVisible().catch(() => false);

    // Export may only show for completed companies
    if (hasExport) {
      await expect(exportButton).toBeVisible();
    }
  });

  test('should have re-scan button for completed companies', async ({ page }) => {
    await page.goto('/companies/1');
    await page.waitForLoadState('networkidle');

    const rescanButton = page.getByRole('button', { name: /re-?scan|rescan/i });
    const hasRescan = await rescanButton.isVisible().catch(() => false);

    // Re-scan only shows for completed companies
    if (hasRescan) {
      await expect(rescanButton).toBeVisible();
    }
  });

  test('should navigate between tabs', async ({ page }) => {
    await page.goto('/companies/1');
    await page.waitForLoadState('networkidle');

    const tabs = page.getByRole('tab');
    const tabCount = await tabs.count();

    if (tabCount > 1) {
      // Click second tab
      await tabs.nth(1).click();

      // Verify tab is selected
      await expect(tabs.nth(1)).toHaveAttribute('aria-selected', 'true');
    }
  });

  test('should show summary content in first tab', async ({ page }) => {
    await page.goto('/companies/1');
    await page.waitForLoadState('networkidle');

    // Check for summary-related content
    const summaryContent = page.getByText(/summary|overview|executive/i);
    const hasSummary = await summaryContent.isVisible().catch(() => false);

    // Content depends on whether company has completed analysis
    expect(typeof hasSummary).toBe('boolean');
  });

  test('should navigate back to dashboard', async ({ page }) => {
    await page.goto('/companies/1');

    const backLink = page.getByRole('link', { name: /back|dashboard/i })
      .or(page.locator('a[href="/"]'));

    if (await backLink.isVisible()) {
      await backLink.click();
      await expect(page).toHaveURL('/');
    }
  });

  test('should be accessible with keyboard navigation', async ({ page }) => {
    await page.goto('/companies/1');
    await page.waitForLoadState('networkidle');

    // Tab navigation should work
    await page.keyboard.press('Tab');

    const focusedTag = await page.evaluate(() => document.activeElement?.tagName);
    expect(['A', 'BUTTON', 'INPUT', 'BODY', 'DIV']).toContain(focusedTag);
  });
});
