import { test, expect } from '@playwright/test';

test('check PII demo after selecting feature', async ({ page }) => {
  await page.goto('http://localhost:3000/features');
  console.log('Navigated to features page');
  
  // Wait for page to load
  await page.waitForLoadState('networkidle');
  
  // Look for Enterprise PII Protection feature card and click it
  const piiCard = page.locator('text=Enterprise PII Protection').first();
  await piiCard.click();
  console.log('Clicked Enterprise PII Protection feature');
  
  // Wait a moment for the interactive demo to appear
  await page.waitForTimeout(1000);
  
  // Take screenshot
  await page.screenshot({ path: '../../pii-demo-active.png', fullPage: true });
  console.log('Screenshot saved');
  
  // Check for interactive demo elements
  const loadSampleVisible = await page.isVisible('button:has-text("Load Sample")').catch(() => false);
  const redactButtonVisible = await page.isVisible('button:has-text("Redact")').catch(() => false);
  
  console.log('Load Sample button visible:', loadSampleVisible);
  console.log('Redact button visible:', redactButtonVisible);
  
  expect(loadSampleVisible || redactButtonVisible).toBeTruthy();
});
