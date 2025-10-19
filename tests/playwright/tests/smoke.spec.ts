import { test, expect } from '@playwright/test';

const HOME_HEADING = /Automation-led RCA/i;

test.describe('RCA Insight Engine smoke journey', () => {
  test('renders landing experience with key navigation', async ({ page }) => {
    await page.goto('/');

  await expect(page.getByRole('heading', { level: 1, name: HOME_HEADING })).toBeVisible();
  await expect(page.getByText(/Executive Operations Control/i)).toBeVisible();

  await expect(page.getByRole('link', { name: 'Dashboard', exact: true })).toBeVisible();
  await expect(page.getByRole('link', { name: 'Jobs', exact: true })).toBeVisible();
  await expect(page.getByRole('link', { name: 'Tickets', exact: true })).toBeVisible();

  await expect(page.getByText(/Total Runs/i)).toBeVisible();
  await expect(page.getByRole('button', { name: /Open Control Center/i })).toBeVisible();
  });

  test('navigates to jobs workspace and exposes ledger table', async ({ page }) => {
    await page.goto('/');

    await page.getByRole('link', { name: 'Jobs', exact: true }).click();
    await expect(page).toHaveURL(/\/jobs$/);

    await expect(page.getByRole('heading', { level: 1, name: /Jobs keep pace/i })).toBeVisible();
    await expect(page.getByRole('table', { name: /Automation jobs/i })).toBeVisible();
    await expect(page.getByRole('button', { name: /Refresh data/i })).toBeVisible();
  });
});
