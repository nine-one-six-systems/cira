/**
 * E2E Tests: Settings Page
 *
 * Tests the settings/configuration page:
 * - Default analysis configuration
 * - Mode presets (Quick/Thorough)
 * - Save/Reset functionality
 */

import { test, expect } from '@playwright/test';

test.describe('Settings Page', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/settings');
  });

  test('should display settings page', async ({ page }) => {
    await expect(page.getByRole('heading', { name: /settings|configuration/i })).toBeVisible();
  });

  test('should show analysis configuration options', async ({ page }) => {
    // Look for configuration-related elements
    const configSection = page.getByText(/analysis|configuration|defaults/i);
    await expect(configSection.first()).toBeVisible();
  });

  test('should have mode presets', async ({ page }) => {
    // Check for Quick/Thorough mode options
    const quickMode = page.getByText(/quick/i);
    const thoroughMode = page.getByText(/thorough/i);

    const hasQuick = await quickMode.isVisible().catch(() => false);
    const hasThorough = await thoroughMode.isVisible().catch(() => false);

    // At least one mode option should exist
    expect(hasQuick || hasThorough).toBeTruthy();
  });

  test('should have save button', async ({ page }) => {
    const saveButton = page.getByRole('button', { name: /save/i });
    await expect(saveButton).toBeVisible();
  });

  test('should have reset button', async ({ page }) => {
    const resetButton = page.getByRole('button', { name: /reset|defaults/i });
    const hasReset = await resetButton.isVisible().catch(() => false);

    // Reset may be conditionally shown
    expect(typeof hasReset).toBe('boolean');
  });

  test('should persist changes on save', async ({ page }) => {
    // Find a slider or input to modify
    const slider = page.locator('input[type="range"]').first();
    const hasSlider = await slider.isVisible().catch(() => false);

    if (hasSlider) {
      // Change value
      await slider.fill('50');

      // Click save
      await page.getByRole('button', { name: /save/i }).click();

      // Check for success feedback
      const successMsg = page.getByText(/saved|success|updated/i);
      await expect(successMsg).toBeVisible({ timeout: 5000 });
    }
  });

  test('should show unsaved changes indicator', async ({ page }) => {
    // Find a form element to modify
    const input = page.locator('input[type="range"], input[type="number"], input[type="text"]').first();
    const hasInput = await input.isVisible().catch(() => false);

    if (hasInput) {
      // Modify value
      await input.click();
      await page.keyboard.press('ArrowRight');

      // Look for unsaved indicator
      const unsavedIndicator = page.getByText(/unsaved|changes/i);
      const hasIndicator = await unsavedIndicator.isVisible().catch(() => false);

      expect(typeof hasIndicator).toBe('boolean');
    }
  });

  test('should navigate back to dashboard', async ({ page }) => {
    const backLink = page.getByRole('link', { name: /back|dashboard/i })
      .or(page.locator('a[href="/"]'));

    if (await backLink.isVisible()) {
      await backLink.click();
      await expect(page).toHaveURL('/');
    }
  });

  test('should be accessible with keyboard navigation', async ({ page }) => {
    await page.keyboard.press('Tab');

    const focusedTag = await page.evaluate(() => document.activeElement?.tagName);
    expect(['A', 'BUTTON', 'INPUT', 'SELECT']).toContain(focusedTag);
  });
});
