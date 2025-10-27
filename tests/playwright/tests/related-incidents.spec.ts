import { test, expect } from '@playwright/test';

test.describe('Related Incidents Feature', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/related');
  });

  test('renders related incidents page with correct heading', async ({ page }) => {
    await expect(page.getByRole('heading', { level: 1, name: /Discover related incidents/i })).toBeVisible();
    await expect(page.getByText(/Compare a completed RCA session/i)).toBeVisible();
  });

  test('displays search mode toggle buttons', async ({ page }) => {
    await expect(page.getByRole('button', { name: /Lookup by session/i })).toBeVisible();
    await expect(page.getByRole('button', { name: /Search by description/i })).toBeVisible();
  });

  test('displays session lookup form controls', async ({ page }) => {
    // Session ID input
    const sessionInput = page.getByRole('textbox', { name: /rca-session-id/i });
    await expect(sessionInput).toBeVisible();
    
    // Relevance slider
    const relevanceSlider = page.getByRole('slider', { name: /Minimum relevance/i });
    await expect(relevanceSlider).toBeVisible();
    await expect(page.getByText(/Minimum relevance: 60%/i)).toBeVisible();
    
    // Limit spinbutton
    const limitInput = page.getByRole('spinbutton');
    await expect(limitInput).toBeVisible();
    await expect(limitInput).toHaveValue('10');
    
    // Platform filter
    const platformFilter = page.getByRole('combobox', { name: /Platform filter/i });
    await expect(platformFilter).toBeVisible();
  });

  test('platform filter has correct options', async ({ page }) => {
    const platformFilter = page.getByRole('combobox', { name: /Platform filter/i });
    await expect(platformFilter).toBeVisible();

    // Check dropdown options count
    await expect(platformFilter.locator('option')).toHaveCount(6);
    
    // Verify option text content
    const options = await platformFilter.locator('option').allTextContents();
    expect(options).toContain('Any platform');
    expect(options).toContain('UiPath');
    expect(options).toContain('Blue Prism');
    expect(options).toContain('Automation Anywhere');
    expect(options).toContain('Appian');
    expect(options).toContain('Pega');
  });  test('displays preview dataset with sample incidents', async ({ page }) => {
    await expect(page.getByRole('heading', { level: 2, name: /Suggested precedents/i })).toBeVisible();
    await expect(page.getByText(/Matches ranked by similarity score/i)).toBeVisible();
    
    // Check for preview dataset label
    await expect(page.getByText(/Preview dataset/i)).toBeVisible();
    
    // Check for sample incidents
    await expect(page.getByText(/Session sess-4521/i)).toBeVisible();
    await expect(page.getByText(/Automation flaked after orchestrator patch rollout/i)).toBeVisible();
    await expect(page.getByText(/Relevance 82%/i)).toBeVisible();
    
    await expect(page.getByText(/Session sess-4319/i)).toBeVisible();
    await expect(page.getByText(/AI summariser misrouted approvals/i)).toBeVisible();
    
    await expect(page.getByText(/Session sess-3982/i)).toBeVisible();
    await expect(page.getByText(/Tenant-wide timeout cascade/i)).toBeVisible();
  });

  test('displays platform badges for incidents', async ({ page }) => {
    await expect(page.getByText(/Platform UiPath/i)).toBeVisible();
    await expect(page.getByText(/Platform Automation Anywhere/i)).toBeVisible();
    await expect(page.getByText(/Platform Blue Prism/i)).toBeVisible();
  });

  test('displays guardrail badges', async ({ page }) => {
    await expect(page.getByText(/CROSS_WORKSPACE/i)).toBeVisible();
    await expect(page.getByText(/AUDIT_TRAIL/i)).toBeVisible();
    await expect(page.getByText(/HUMAN_REVIEW/i)).toBeVisible();
  });

  test('run similarity lookup button is visible', async ({ page }) => {
    const lookupButton = page.getByRole('button', { name: /Run similarity lookup/i });
    await expect(lookupButton).toBeVisible();
  });

  test('can adjust relevance slider', async ({ page }) => {
    const slider = page.getByRole('slider', { name: /Minimum relevance/i });
    
    // Get initial value
    const initialValue = await slider.getAttribute('value');
    expect(initialValue).toBe('0.6'); // 60%
    
    // Adjust slider (this is a visual test, actual API call would require backend)
    await slider.fill('0.8');
    
    // Verify the label updates
    await expect(page.getByText(/Minimum relevance: 80%/i)).toBeVisible();
  });

  test('can adjust limit spinbutton', async ({ page }) => {
    const limitInput = page.getByRole('spinbutton');
    
    // Change limit value
    await limitInput.fill('20');
    await expect(limitInput).toHaveValue('20');
    
    // Change back
    await limitInput.fill('5');
    await expect(limitInput).toHaveValue('5');
  });

  test('can select different platform filters', async ({ page }) => {
    const platformFilter = page.getByRole('combobox', { name: /Platform filter/i });
    
    // Select UiPath (value is the same as display text)
    await platformFilter.selectOption('UiPath');
    await expect(platformFilter).toHaveValue('UiPath');
    
    // Select Blue Prism
    await platformFilter.selectOption('Blue Prism');
    await expect(platformFilter).toHaveValue('Blue Prism');
    
    // Select Any platform (empty string value)
    await platformFilter.selectOption('');
    await expect(platformFilter).toHaveValue('');
  });

  test('can switch between lookup modes', async ({ page }) => {
    const sessionButton = page.getByRole('button', { name: /Lookup by session/i });
    const descriptionButton = page.getByRole('button', { name: /Search by description/i });
    
    // Initially on session lookup
    await expect(sessionButton).toBeVisible();
    
    // Switch to description mode
    await descriptionButton.click();
    
    // Should still see both buttons
    await expect(sessionButton).toBeVisible();
    await expect(descriptionButton).toBeVisible();
  });

  test('has accessible navigation back to main pages', async ({ page }) => {
    // Check main navigation is present
    await expect(page.getByRole('link', { name: 'Dashboard', exact: true })).toBeVisible();
    await expect(page.getByRole('link', { name: 'Features', exact: true })).toBeVisible();
    await expect(page.getByRole('link', { name: 'Investigate', exact: true })).toBeVisible();
  });
});
