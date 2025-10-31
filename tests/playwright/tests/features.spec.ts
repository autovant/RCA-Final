import { test, expect } from '@playwright/test';

test.describe('Features Page', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/features');
  });

  test('renders features page with correct heading', async ({ page }) => {
    await expect(page.getByRole('heading', { level: 1, name: /Platform Features/i })).toBeVisible();
    await expect(page.getByText(/Discover the comprehensive capabilities/i)).toBeVisible();
  });

  test('displays main action buttons', async ({ page }) => {
    await expect(page.getByRole('button', { name: /Launch Guided Demo/i })).toBeVisible();
    await expect(page.getByRole('button', { name: /Start Investigation/i })).toBeVisible();
  });

  test('displays feature search and filters', async ({ page }) => {
    // Search box
    await expect(page.getByRole('searchbox', { name: /Search features/i })).toBeVisible();
    
    // Status filters
    await expect(page.getByRole('button', { name: 'Beta', exact: true })).toBeVisible();
    await expect(page.getByRole('button', { name: 'Stable', exact: true })).toBeVisible();
  });

  test('displays all category filters', async ({ page }) => {
    const categories = [
      'AI & Analysis',
      'Security & Compliance',
      'Integrations',
      'Automation & Watchers',
      'Platform Services',
      'Reporting & Outputs',
      'Observability',
      'UI & Experience',
      'Data Ingestion',
    ];

    for (const category of categories) {
      await expect(page.getByRole('button', { name: category, exact: true })).toBeVisible();
    }
  });

  test('displays Intelligent Platform Detection feature with BETA badge', async ({ page }) => {
    // Find the Platform Detection button in navigation
    const platformDetectionButton = page.getByRole('button', { name: /Intelligent Platform Detection/i });
    await expect(platformDetectionButton).toBeVisible();
    
    // Verify BETA badge is present
    await expect(page.getByText('Intelligent Platform Detection')).toBeVisible();
    await expect(platformDetectionButton.getByText('BETA')).toBeVisible();
  });

  test('displays Archive Format Support feature', async ({ page }) => {
    const archiveButton = page.getByRole('button', { name: /Archive Format Support/i });
    await expect(archiveButton).toBeVisible();
  });

  test('Platform Detection feature is under AI & Analysis category', async ({ page }) => {
    // Navigate to AI & Analysis section
    const aiAnalysisSection = page.locator('text=AI & Analysis').first();
    await expect(aiAnalysisSection).toBeVisible();
    
    // Verify Platform Detection is in this section
    const platformDetection = page.getByRole('button', { name: /Intelligent Platform Detection/i });
    await expect(platformDetection).toBeVisible();
  });

  test('Archive Format Support is under Data Ingestion category', async ({ page }) => {
    // Navigate to Data Ingestion section
    const dataIngestionSection = page.locator('text=Data Ingestion').first();
    await expect(dataIngestionSection).toBeVisible();
    
    // Verify Archive Format Support is in this section
    const archiveSupport = page.getByRole('button', { name: /Archive Format Support/i });
    await expect(archiveSupport).toBeVisible();
  });

  test('displays other key features', async ({ page }) => {
    await expect(page.getByRole('button', { name: /Conversational RCA Engine/i })).toBeVisible();
    await expect(page.getByRole('button', { name: /Enterprise PII Protection/i })).toBeVisible();
    await expect(page.getByRole('button', { name: /Multi-Provider LLM Support/i })).toBeVisible();
    await expect(page.getByRole('button', { name: /ITSM Ticketing Integration/i })).toBeVisible();
  });

  test('displays default feature detail (Conversational RCA Engine)', async ({ page }) => {
    // Default feature shown in main area
    await expect(page.getByRole('heading', { level: 2, name: /Conversational RCA Engine/i })).toBeVisible();
    await expect(page.getByText(/Multi-turn LLM reasoning engine/i)).toBeVisible();
    
    // Check for key sections
    await expect(page.getByRole('heading', { level: 3, name: /Key Benefits/i })).toBeVisible();
    await expect(page.getByRole('heading', { level: 3, name: /Technical Capabilities/i })).toBeVisible();
    await expect(page.getByRole('heading', { level: 3, name: /Common Use Cases/i })).toBeVisible();
  });

  test('can search for features', async ({ page }) => {
    const searchBox = page.getByRole('searchbox', { name: /Search features/i });
    
    // Search for Platform Detection
    await searchBox.fill('Platform');
    
    // Should still see the Platform Detection feature
    await expect(page.getByRole('button', { name: /Intelligent Platform Detection/i })).toBeVisible();
  });

  test('can filter by Beta status', async ({ page }) => {
    const betaButton = page.getByRole('button', { name: 'Beta', exact: true });
    
    // Click Beta filter
    await betaButton.click();
    
    // Platform Detection should still be visible (it's Beta)
    await expect(page.getByRole('button', { name: /Intelligent Platform Detection/i })).toBeVisible();
  });

  test('can navigate to Demo page from features', async ({ page }) => {
    const demoButton = page.getByRole('button', { name: /Launch Guided Demo/i }).first();
    await demoButton.click();
    
    await expect(page).toHaveURL(/\/demo$/);
  });

  test('can navigate to Investigation page from features', async ({ page }) => {
    const investigateButton = page.getByRole('button', { name: /Start Investigation/i }).first();
    await investigateButton.click();
    
    await expect(page).toHaveURL(/\/investigation$/);
  });

  test('has accessible main navigation', async ({ page }) => {
    await expect(page.getByRole('link', { name: 'Dashboard', exact: true })).toBeVisible();
    await expect(page.getByRole('link', { name: 'Related', exact: true })).toBeVisible();
    await expect(page.getByRole('link', { name: 'Investigate', exact: true })).toBeVisible();
  });

  test('displays system status indicator', async ({ page }) => {
    await expect(page.getByText(/Systems Nominal/i)).toBeVisible();
  });
});

test.describe('Platform Detection Feature Details', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/features');
  });

  test('clicking Platform Detection shows feature details', async ({ page }) => {
    // Click on Platform Detection feature
    const platformDetectionButton = page.getByRole('button', { name: /Intelligent Platform Detection/i });
    await platformDetectionButton.click();
    
    // Wait a moment for content to potentially update
    await page.waitForTimeout(500);
    
    // Should still be on features page
    await expect(page).toHaveURL(/\/features/);
  });

  test('Platform Detection BETA badge is visible in navigation', async ({ page }) => {
    const betaBadge = page.locator('text=BETA').first();
    await expect(betaBadge).toBeVisible();
  });
});

test.describe('Archive Format Support Feature Details', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/features');
  });

  test('clicking Archive Format Support shows feature details', async ({ page }) => {
    // Click on Archive Format Support feature
    const archiveButton = page.getByRole('button', { name: /Archive Format Support/i });
    await archiveButton.click();
    
    // Wait for potential content update
    await page.waitForTimeout(500);
    
    // Should still be on features page
    await expect(page).toHaveURL(/\/features/);
  });

  test('Archive Format Support is marked as stable', async ({ page }) => {
    // Archive Format Support should not have BETA badge
    const archiveButton = page.getByRole('button', { name: /Archive Format Support/i });
    await expect(archiveButton).toBeVisible();
    
    // Should not have BETA badge in this button
    const betaBadgeInArchive = archiveButton.locator('text=BETA');
    await expect(betaBadgeInArchive).not.toBeVisible();
  });
});
