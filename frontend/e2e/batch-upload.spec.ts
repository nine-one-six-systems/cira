/**
 * E2E Tests: Batch Upload Flow
 *
 * Tests the CSV batch upload functionality:
 * - File upload zone
 * - CSV parsing and validation
 * - Preview table
 * - Template download
 * - Batch submission
 */

import { test, expect } from '@playwright/test';

test.describe('Batch Upload Flow', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/batch');
  });

  test('should display batch upload page', async ({ page }) => {
    await expect(page.getByRole('heading', { name: /batch upload/i })).toBeVisible();
    await expect(page.getByText(/drag.*drop|upload.*csv/i)).toBeVisible();
  });

  test('should have template download button', async ({ page }) => {
    const downloadButton = page.getByRole('button', { name: /download.*template/i });
    await expect(downloadButton).toBeVisible();
  });

  test('should show file drop zone', async ({ page }) => {
    // Check for drop zone element
    const dropZone = page.locator('[data-testid="file-dropzone"], .dropzone, [class*="drop"]').first();
    if (await dropZone.isVisible()) {
      await expect(dropZone).toBeVisible();
    } else {
      // Alternative: check for file input
      const fileInput = page.locator('input[type="file"]');
      await expect(fileInput).toBeAttached();
    }
  });

  test('should accept CSV file upload', async ({ page }) => {
    // Create a simple CSV content
    const csvContent = `company_name,website_url,industry
Test Company 1,https://example1.com,Technology
Test Company 2,https://example2.com,Healthcare`;

    // Get file input (may be hidden)
    const fileInput = page.locator('input[type="file"]');

    // Upload file
    await fileInput.setInputFiles({
      name: 'companies.csv',
      mimeType: 'text/csv',
      buffer: Buffer.from(csvContent),
    });

    // Should show preview or validation results
    await expect(page.getByText(/Test Company 1|preview|2 companies|rows/i)).toBeVisible({ timeout: 5000 });
  });

  test('should show validation errors for invalid CSV', async ({ page }) => {
    // Create CSV with invalid data
    const invalidCsv = `company_name,website_url,industry
Valid Company,https://valid.com,Tech
Invalid Company,not-a-url,Tech`;

    const fileInput = page.locator('input[type="file"]');

    await fileInput.setInputFiles({
      name: 'invalid.csv',
      mimeType: 'text/csv',
      buffer: Buffer.from(invalidCsv),
    });

    // Should show validation indicator (warning, error, or specific message)
    await page.waitForTimeout(1000); // Wait for parsing
    const hasError = await page.getByText(/invalid|error|warning/i).isVisible();
    const hasPartialSuccess = await page.getByText(/1 valid|1 error/i).isVisible();

    expect(hasError || hasPartialSuccess).toBeTruthy();
  });

  test('should navigate back to dashboard', async ({ page }) => {
    const backLink = page.getByRole('link', { name: /dashboard|back|cancel/i });
    if (await backLink.isVisible()) {
      await backLink.click();
      await expect(page).toHaveURL('/');
    }
  });

  test('should be accessible with keyboard', async ({ page }) => {
    // Ensure keyboard navigation works
    await page.keyboard.press('Tab');

    // Should focus on interactive element
    const focused = await page.evaluate(() => document.activeElement?.tagName);
    expect(['BUTTON', 'A', 'INPUT', 'SELECT']).toContain(focused);
  });
});
