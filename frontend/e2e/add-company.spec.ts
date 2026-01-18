/**
 * E2E Tests: Add Company Flow
 *
 * Tests the single company creation flow:
 * - Form validation
 * - URL validation
 * - Advanced configuration
 * - Submission and redirect to progress
 */

import { test, expect } from '@playwright/test';

test.describe('Add Company Flow', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/add');
  });

  test('should display add company form', async ({ page }) => {
    await expect(page.getByRole('heading', { name: /add company/i })).toBeVisible();
    await expect(page.getByLabel(/company name/i)).toBeVisible();
    await expect(page.getByLabel(/website url/i)).toBeVisible();
  });

  test('should validate required fields', async ({ page }) => {
    // Try to submit empty form
    await page.getByRole('button', { name: /start analysis/i }).click();

    // Should show validation errors
    await expect(page.getByText(/company name is required/i)).toBeVisible();
  });

  test('should validate URL format', async ({ page }) => {
    await page.getByLabel(/company name/i).fill('Test Company');
    await page.getByLabel(/website url/i).fill('not-a-valid-url');

    await page.getByRole('button', { name: /start analysis/i }).click();

    // Should show URL validation error
    await expect(page.getByText(/invalid url/i)).toBeVisible();
  });

  test('should toggle advanced configuration', async ({ page }) => {
    // Check advanced config is collapsed by default
    const advancedSection = page.getByText(/advanced configuration/i);
    await expect(advancedSection).toBeVisible();

    // Click to expand
    await advancedSection.click();

    // Should show configuration options
    await expect(page.getByText(/max pages/i)).toBeVisible();
    await expect(page.getByText(/max depth/i)).toBeVisible();
  });

  test('should fill form and submit successfully', async ({ page }) => {
    // Fill required fields
    await page.getByLabel(/company name/i).fill('Anthropic');
    await page.getByLabel(/website url/i).fill('https://anthropic.com');

    // Select industry if available
    const industrySelect = page.getByLabel(/industry/i);
    if (await industrySelect.isVisible()) {
      await industrySelect.selectOption({ index: 1 });
    }

    // Submit form
    await page.getByRole('button', { name: /start analysis/i }).click();

    // Should redirect to progress page (or show success message)
    await expect(page).toHaveURL(/\/companies\/\d+\/progress|\/companies\/[a-zA-Z0-9-]+\/progress/, { timeout: 10000 });
  });

  test('should navigate back to dashboard', async ({ page }) => {
    await page.getByRole('link', { name: /dashboard|back|cancel/i }).click();
    await expect(page).toHaveURL('/');
  });

  test('should be accessible with keyboard navigation', async ({ page }) => {
    // Tab through form fields
    await page.keyboard.press('Tab');
    await expect(page.getByLabel(/company name/i)).toBeFocused();

    await page.keyboard.press('Tab');
    await expect(page.getByLabel(/website url/i)).toBeFocused();
  });
});
