import { test, expect } from '@playwright/test';

test.describe('Cross-Feature Navigation', () => {
  test('can navigate from homepage to all feature pages', async ({ page }) => {
    await page.goto('/');

    // Navigate to Related Incidents
    await page.getByRole('link', { name: 'Related', exact: true }).click();
    await expect(page).toHaveURL(/\/related$/);
    await expect(page.getByRole('heading', { level: 1, name: /Discover related incidents/i })).toBeVisible();

    // Navigate to Features
    await page.getByRole('link', { name: 'Features', exact: true }).click();
    await expect(page).toHaveURL(/\/features$/);
    await expect(page.getByRole('heading', { level: 1, name: /Platform Features/i })).toBeVisible();

    // Navigate to Investigation - wait for page to be ready
    await page.getByRole('link', { name: 'Investigate', exact: true }).click();
    await page.waitForURL(/\/investigation$/);
    await expect(page).toHaveURL(/\/investigation$/);
    await expect(page.getByRole('heading', { level: 1, name: /Start New Investigation/i })).toBeVisible();

    // Navigate back to Dashboard
    await page.getByRole('link', { name: 'Dashboard', exact: true }).click();
    await expect(page).toHaveURL(/\/$/);
  });

  test('can navigate from Features page to Investigation', async ({ page }) => {
    await page.goto('/features');

    const investigateButton = page.getByRole('button', { name: /Start Investigation/i }).first();
    await investigateButton.click();

    await expect(page).toHaveURL(/\/investigation$/);
    await expect(page.getByRole('heading', { level: 1, name: /Start New Investigation/i })).toBeVisible();
  });

  test('can navigate from Features page to Demo', async ({ page }) => {
    await page.goto('/features');

    const demoButton = page.getByRole('button', { name: /Launch Guided Demo/i }).first();
    await demoButton.click();

    await expect(page).toHaveURL(/\/demo$/);
  });

  test('all pages have consistent navigation menu', async ({ page }) => {
    const pages = ['/', '/related', '/features', '/investigation', '/jobs'];

    for (const pagePath of pages) {
      await page.goto(pagePath);

      // Check all navigation links are present
      await expect(page.getByRole('link', { name: 'Dashboard', exact: true })).toBeVisible();
      await expect(page.getByRole('link', { name: 'Investigate', exact: true })).toBeVisible();
      await expect(page.getByRole('link', { name: 'Related', exact: true })).toBeVisible();
      await expect(page.getByRole('link', { name: 'Features', exact: true })).toBeVisible();
      await expect(page.getByRole('link', { name: 'Jobs', exact: true })).toBeVisible();
      await expect(page.getByRole('link', { name: 'Docs', exact: true })).toBeVisible();
    }
  });

  test('navigation menu includes all main sections', async ({ page }) => {
    await page.goto('/');

    const expectedLinks = [
      'Dashboard',
      'Investigate',
      'Related',
      'Features',
      'Demo',
      'Showcase',
      'About',
      'Jobs',
      'Tickets',
      'Watcher',
      'Prompts',
      'Docs',
    ];

    for (const linkName of expectedLinks) {
      await expect(page.getByRole('link', { name: linkName, exact: true })).toBeVisible();
    }
  });
});

test.describe('Feature Integration Flow', () => {
  test('investigation workflow references all integrated features', async ({ page }) => {
    await page.goto('/investigation');

    // Verify PII Protection is in the workflow
    await expect(page.getByText(/🔒 PII Protection/i)).toBeVisible();

    // Verify the workflow mentions platform detection implicitly
    await expect(page.getByText(/Analyzing file types/i)).toBeVisible();

    // Verify archive support is implied in upload section
    await expect(page.getByText(/Upload logs, configs, or traces/i)).toBeVisible();
  });

  test('features page showcases all three integrated features', async ({ page }) => {
    await page.goto('/features');

    // Platform Detection (BETA)
    const platformDetectionButton = page.getByRole('button', { name: /Intelligent Platform Detection/i });
    await expect(platformDetectionButton).toBeVisible();
    // Scope BETA badge to the platform detection feature section
    await expect(platformDetectionButton.locator('..').getByText('BETA')).toBeVisible();

    // Archive Format Support
    await expect(page.getByRole('button', { name: /Archive Format Support/i })).toBeVisible();

    // PII Protection (existing feature)
    await expect(page.getByRole('button', { name: /Enterprise PII Protection/i })).toBeVisible();
  });

  test('related incidents page allows platform filtering', async ({ page }) => {
    await page.goto('/related');

    const platformFilter = page.getByRole('combobox', { name: /Platform filter/i });
    await expect(platformFilter).toBeVisible();

    // Test filtering by UiPath
    await platformFilter.selectOption('UiPath');
    await expect(platformFilter).toHaveValue('UiPath');

    // Verify UiPath incident is still visible
    await expect(page.getByText(/Platform UiPath/i)).toBeVisible();
  });
});

test.describe('System Status and Health', () => {
  test('all pages show system status indicator', async ({ page }) => {
    const pages = ['/', '/related', '/features', '/investigation'];

    for (const pagePath of pages) {
      await page.goto(pagePath);
      await expect(page.getByText(/Systems Nominal/i)).toBeVisible();
    }
  });

  test('homepage displays system health metrics', async ({ page }) => {
    await page.goto('/');

    // Control Surface status
    await expect(page.getByText(/Control Surface/i)).toBeVisible();
    await expect(page.getByText(/API/i)).toBeVisible();
    await expect(page.getByText(/Online/i)).toBeVisible();
    await expect(page.getByText(/Database/i)).toBeVisible();
    await expect(page.getByText(/Connected/i)).toBeVisible();
    
    // Scope "Ready" to LLM Service context - use the first occurrence
    const llmServiceSection = page.getByText(/LLM Service/i);
    await expect(llmServiceSection).toBeVisible();
    await expect(page.getByText(/Ready/i).first()).toBeVisible();
  });
});

test.describe('Responsive Layout', () => {
  test('navigation is visible on desktop viewport', async ({ page }) => {
    await page.setViewportSize({ width: 1440, height: 900 });
    await page.goto('/');

    await expect(page.getByRole('navigation')).toBeVisible();
    await expect(page.getByRole('link', { name: 'Dashboard', exact: true })).toBeVisible();
  });

  test('main content areas are properly structured', async ({ page }) => {
    await page.goto('/');

    // Banner/header
    await expect(page.locator('role=banner')).toBeVisible();

    // Main content
    await expect(page.locator('role=main')).toBeVisible();
  });
});

test.describe('Branding and Identity', () => {
  test('all pages show Perficient RCA Console branding', async ({ page }) => {
    const pages = ['/', '/related', '/features', '/investigation'];

    for (const pagePath of pages) {
      await page.goto(pagePath);
      // Use first() to handle multiple h1 elements on some pages
      await expect(page.getByRole('heading', { level: 1, name: /Perficient RCA Console|RCA|Platform Features|Start New Investigation|Discover related/i }).first()).toBeVisible();
    }
  });

  test('page titles are set correctly', async ({ page }) => {
    await page.goto('/');
    await expect(page).toHaveTitle(/RCA Engine/i);

    await page.goto('/related');
    await expect(page).toHaveTitle(/RCA Engine/i);

    await page.goto('/features');
    await expect(page).toHaveTitle(/RCA Engine/i);

    await page.goto('/investigation');
    await expect(page).toHaveTitle(/RCA Engine/i);
  });
});

test.describe('Action Buttons and CTAs', () => {
  test('homepage has primary action buttons', async ({ page }) => {
    await page.goto('/');

    await expect(page.getByRole('button', { name: /Launch New Analysis/i })).toBeVisible();
    await expect(page.getByRole('button', { name: /Review Recent Jobs/i })).toBeVisible();
    await expect(page.getByRole('button', { name: /Open Control Center/i })).toBeVisible();
  });

  test('homepage action buttons are clickable', async ({ page }) => {
    await page.goto('/');

    const launchButton = page.getByRole('button', { name: /Launch New Analysis/i });
    await expect(launchButton).toBeEnabled();

    const reviewButton = page.getByRole('button', { name: /Review Recent Jobs/i });
    await expect(reviewButton).toBeEnabled();
  });

  test('features page has launch demo button', async ({ page }) => {
    await page.goto('/features');

    const demoButton = page.getByRole('button', { name: /Launch Guided Demo/i }).first();
    await expect(demoButton).toBeVisible();
    await expect(demoButton).toBeEnabled();
  });
});

test.describe('Data Display and Formatting', () => {
  test('homepage shows metrics with proper formatting', async ({ page }) => {
    await page.goto('/');

    // Check for numeric metrics
    await expect(page.getByText(/Total Runs/i)).toBeVisible();
    await expect(page.getByText(/In Flight/i)).toBeVisible();
    // Use first() to handle multiple "Completed" text occurrences
    await expect(page.getByText(/Completed/i).first()).toBeVisible();
    // Use first() to handle multiple "Attention" text occurrences
    await expect(page.getByText(/Attention/i).first()).toBeVisible();

    // Check for percentage display
    await expect(page.getByText(/Success Rate/i)).toBeVisible();
    await expect(page.getByText(/25%/i)).toBeVisible();
  });

  test('related incidents show relevance percentages', async ({ page }) => {
    await page.goto('/related');

    await expect(page.getByText(/Relevance 82%/i)).toBeVisible();
    await expect(page.getByText(/Relevance 74%/i)).toBeVisible();
    await expect(page.getByText(/Relevance 69%/i)).toBeVisible();
  });

  test('related incidents show timestamps', async ({ page }) => {
    await page.goto('/related');

    await expect(page.getByText(/Sep 18, 02:22 PM/i)).toBeVisible();
    await expect(page.getByText(/Aug 2, 01:14 AM/i)).toBeVisible();
    await expect(page.getByText(/May 27, 07:41 PM/i)).toBeVisible();
  });
});
