import { test, expect } from '@playwright/test';

test.describe('Investigation Page', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/investigation');
  });

  test('renders investigation page with correct heading', async ({ page }) => {
    await expect(page.getByRole('heading', { level: 1, name: /Start New Investigation/i })).toBeVisible();
    await expect(page.getByText(/Upload files, configure analysis parameters/i)).toBeVisible();
  });

  test('displays three-step workflow structure', async ({ page }) => {
    await expect(page.getByRole('heading', { level: 2, name: /1\. Upload Files/i })).toBeVisible();
    await expect(page.getByRole('heading', { level: 2, name: /2\. Configure Analysis/i })).toBeVisible();
    await expect(page.getByRole('heading', { level: 2, name: /3\. Live Analysis Stream/i })).toBeVisible();
  });

  test('displays file upload section', async ({ page }) => {
    await expect(page.getByText(/Upload logs, configs, or traces for analysis/i)).toBeVisible();
    await expect(page.getByText(/Drop files here or click to browse/i)).toBeVisible();
    await expect(page.getByText(/Supports logs, configs, traces, and documentation files/i)).toBeVisible();
    
    // Upload button
    await expect(page.getByRole('button', { name: /Upload files for analysis/i })).toBeVisible();
  });

  test('displays job configuration section', async ({ page }) => {
    await expect(page.getByRole('heading', { level: 3, name: /Job Configuration/i })).toBeVisible();
    await expect(page.getByText(/Configure the analysis parameters/i)).toBeVisible();
  });

  test('displays job type selector', async ({ page }) => {
    const jobTypeSelect = page.getByRole('combobox', { name: /Job Type/i });
    await expect(jobTypeSelect).toBeVisible();
    
    // Check options count (options are hidden by default in HTML)
    await expect(jobTypeSelect.locator('option')).toHaveCount(3);
    
    // Verify option values exist
    const options = await jobTypeSelect.locator('option').allTextContents();
    expect(options).toContain('RCA Analysis');
    expect(options).toContain('Log Analysis');
    expect(options).toContain('Incident Investigation');
  });

  test('displays provider selector', async ({ page }) => {
    const providerSelect = page.getByRole('combobox', { name: /Provider/i });
    await expect(providerSelect).toBeVisible();
    
    // Check options count (options are hidden by default in HTML)
    await expect(providerSelect.locator('option')).toHaveCount(4);
    
    // Verify option values exist
    const options = await providerSelect.locator('option').allTextContents();
    expect(options).toContain('GitHub Copilot');
    expect(options).toContain('OpenAI');
    expect(options).toContain('Anthropic');
    expect(options).toContain('Ollama (Local)');
  });

  test('displays model selector', async ({ page }) => {
    const modelSelect = page.getByRole('combobox', { name: /^Model$/i });
    await expect(modelSelect).toBeVisible();
    
    // Check options count (options are hidden by default in HTML, provider-dependent)
    const optionCount = await modelSelect.locator('option').count();
    expect(optionCount).toBeGreaterThanOrEqual(3);
    
    // Verify at least GPT-4 options exist (default provider is Copilot)
    const options = await modelSelect.locator('option').allTextContents();
    expect(options.some(opt => opt.includes('GPT'))).toBeTruthy();
  });

  test('displays priority slider', async ({ page }) => {
    const prioritySlider = page.getByRole('slider', { name: /Priority/i });
    await expect(prioritySlider).toBeVisible();
    
    // Check labels
    await expect(page.getByText(/Priority: 5/i)).toBeVisible();
    await expect(page.getByText('Low', { exact: true })).toBeVisible();
    await expect(page.getByText('High', { exact: true })).toBeVisible();
  });

  test('displays prompt template selector with link to view all', async ({ page }) => {
    const promptSelect = page.getByRole('combobox', { name: /Prompt Template/i });
    await expect(promptSelect).toBeVisible();
    
    // View All link
    const viewAllLink = page.getByRole('link', { name: /View All/i });
    await expect(viewAllLink).toBeVisible();
  });

  test('start analysis button is disabled when no files uploaded', async ({ page }) => {
    const startButton = page.getByRole('button', { name: /Start Analysis/i });
    await expect(startButton).toBeVisible();
    await expect(startButton).toBeDisabled();
    
    // Check the message
    await expect(page.getByText(/Upload at least one file to start analysis/i)).toBeVisible();
  });

  test('displays no files uploaded message', async ({ page }) => {
    await expect(page.getByText(/No files uploaded/i)).toBeVisible();
  });

  test('displays live analysis stream section', async ({ page }) => {
    await expect(page.getByRole('heading', { level: 3, name: /Live Analysis Stream/i })).toBeVisible();
    await expect(page.getByText(/Real-time updates from the RCA engine/i)).toBeVisible();
  });

  test('displays stream status indicators', async ({ page }) => {
    await expect(page.getByText('Ready', { exact: true })).toBeVisible();
    await expect(page.getByText('Offline', { exact: true })).toBeVisible();
  });

  test('displays analysis progress steps', async ({ page }) => {
    await expect(page.getByRole('heading', { level: 4, name: /Analysis Progress/i })).toBeVisible();
    
    // Check all 9 progress steps
    await expect(page.getByText(/Classifying uploaded files/i)).toBeVisible();
    await expect(page.getByText(/Segmenting content into analysis-ready chunks/i)).toBeVisible();
    await expect(page.getByText(/Generating semantic embeddings/i)).toBeVisible();
    await expect(page.getByText(/Storing structured insights/i)).toBeVisible();
    await expect(page.getByText(/Correlating with historical incidents/i)).toBeVisible();
    await expect(page.getByText(/Running AI-powered root cause analysis/i)).toBeVisible();
    await expect(page.getByText(/Preparing final RCA report/i)).toBeVisible();
    await expect(page.getByText(/Analysis completed successfully/i)).toBeVisible();
  });

  test('displays PII Protection step prominently', async ({ page }) => {
    // This is the key feature we integrated
    const piiStep = page.getByText(/🔒 PII Protection: Scanning & Redacting Sensitive Data/i);
    await expect(piiStep).toBeVisible();
    
    // Check description
    await expect(page.getByText(/Multi-pass scanning for credentials, secrets, and personal data/i)).toBeVisible();
  });

  test('PII Protection step is positioned correctly in workflow', async ({ page }) => {
    // Get all step texts
    const steps = await page.locator('ul li').allTextContents();
    
    // PII Protection should be step 2 (after classifying files)
    const piiStepIndex = steps.findIndex(step => step.includes('PII Protection'));
    expect(piiStepIndex).toBe(1); // 0-indexed, so position 1 is step 2
  });

  test('displays activity log section', async ({ page }) => {
    await expect(page.getByRole('heading', { level: 4, name: /📋 Activity Log/i })).toBeVisible();
    await expect(page.getByText(/0 events/i)).toBeVisible();
    
    // Export button should be disabled when no events
    const exportButton = page.getByRole('button', { name: /Export Log/i });
    await expect(exportButton).toBeVisible();
    await expect(exportButton).toBeDisabled();
  });

  test('displays waiting for activity message', async ({ page }) => {
    await expect(page.getByText(/📭/i)).toBeVisible();
    await expect(page.getByText(/Waiting for activity.../i)).toBeVisible();
    await expect(page.getByText(/Real-time events will stream here during analysis/i)).toBeVisible();
  });

  test('can change job type', async ({ page }) => {
    const jobTypeSelect = page.getByRole('combobox', { name: /Job Type/i });
    
    await jobTypeSelect.selectOption('log_analysis');
    await expect(jobTypeSelect).toHaveValue('log_analysis');
    
    await jobTypeSelect.selectOption('incident_investigation');
    await expect(jobTypeSelect).toHaveValue('incident_investigation');
  });

  test('can change provider', async ({ page }) => {
    const providerSelect = page.getByRole('combobox', { name: /Provider/i });
    
    await providerSelect.selectOption('openai');
    await expect(providerSelect).toHaveValue('openai');
    
    await providerSelect.selectOption('anthropic');
    await expect(providerSelect).toHaveValue('anthropic');
  });

  test('can change model', async ({ page }) => {
    const modelSelect = page.getByRole('combobox', { name: /^Model$/i });
    
    await modelSelect.selectOption('gpt-4o');
    await expect(modelSelect).toHaveValue('gpt-4o');
    
    await modelSelect.selectOption('gpt-3.5-turbo');
    await expect(modelSelect).toHaveValue('gpt-3.5-turbo');
  });

  test('can adjust priority slider', async ({ page }) => {
    const prioritySlider = page.getByRole('slider', { name: /Priority/i });
    
    // Change priority
    await prioritySlider.fill('8');
    
    // Verify the slider value changed
    await expect(prioritySlider).toHaveValue('8');
    
    // Verify label updates (format: "Priority: 8")
    await expect(page.getByText('Priority: 8')).toBeVisible();
  });

  test('has accessible main navigation', async ({ page }) => {
    await expect(page.getByRole('link', { name: 'Dashboard', exact: true })).toBeVisible();
    await expect(page.getByRole('link', { name: 'Related', exact: true })).toBeVisible();
    await expect(page.getByRole('link', { name: 'Features', exact: true })).toBeVisible();
  });

  test('can navigate to prompts page from view all link', async ({ page, context }) => {
    const viewAllLink = page.getByRole('link', { name: /View All/i });
    
    // Link opens in new tab/window, so listen for new page
    const [newPage] = await Promise.all([
      context.waitForEvent('page'),
      viewAllLink.click()
    ]);
    
    await newPage.waitForLoadState();
    await expect(newPage).toHaveURL(/\/prompts$/);
  });
});

test.describe('Investigation Page - Archive Format Support', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/investigation');
  });

  test('upload section mentions supported file types', async ({ page }) => {
    await expect(page.getByText(/Supports logs, configs, traces, and documentation files/i)).toBeVisible();
  });

  test('file upload area is interactive', async ({ page }) => {
    const uploadButton = page.getByRole('button', { name: /Upload files for analysis/i });
    await expect(uploadButton).toBeVisible();
    await expect(uploadButton).toBeEnabled();
  });

  // Note: Actual file upload testing would require backend running
  // This test verifies the UI is ready for file uploads
  test('upload area shows drop zone text', async ({ page }) => {
    await expect(page.getByText(/Drop files here or click to browse/i)).toBeVisible();
  });
});

test.describe('Investigation Page - Complete Workflow Visibility', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/investigation');
  });

  test('all 9 analysis steps are visible', async ({ page }) => {
    const steps = [
      'Classifying uploaded files',
      '🔒 PII Protection: Scanning & Redacting Sensitive Data',
      'Segmenting content into analysis-ready chunks',
      'Generating semantic embeddings',
      'Storing structured insights',
      'Correlating with historical incidents',
      'Running AI-powered root cause analysis',
      'Preparing final RCA report',
      'Analysis completed successfully',
    ];

    for (const step of steps) {
      await expect(page.getByText(step)).toBeVisible();
    }
  });

  test('step descriptions provide context', async ({ page }) => {
    await expect(page.getByText(/Analyzing file types and preparing analysis pipeline/i)).toBeVisible();
    await expect(page.getByText(/Multi-pass scanning for credentials, secrets, and personal data/i)).toBeVisible();
    await expect(page.getByText(/Breaking documents into analysis-ready chunks/i)).toBeVisible();
    await expect(page.getByText(/Creating semantic vectors for similarity search/i)).toBeVisible();
  });
});
