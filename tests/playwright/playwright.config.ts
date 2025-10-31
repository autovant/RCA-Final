import { defineConfig, devices } from '@playwright/test';

const defaultBaseUrl = 'http://localhost:3000';

export default defineConfig({
  testDir: './tests',
  fullyParallel: true,
  timeout: 60_000,
  expect: {
    timeout: 5_000,
  },
  retries: process.env.CI ? 2 : 0,
  reporter: process.env.CI
    ? [
        ['list'],
        ['html', { outputFolder: 'playwright-report', open: 'never' }],
      ]
    : [['list'], ['html', { open: 'on-failure' }]],
  use: {
    baseURL: process.env.PLAYWRIGHT_BASE_URL || defaultBaseUrl,
    trace: 'retain-on-failure',
    screenshot: 'only-on-failure',
    video: 'retain-on-failure',
    viewport: { width: 1440, height: 900 },
  },
  webServer: {
    command: 'cd ../../ui && npm run dev',
    url: defaultBaseUrl,
    reuseExistingServer: !process.env.CI,
    timeout: 120_000,
    stdout: 'ignore',
    stderr: 'pipe',
  },
  projects: [
    {
      name: 'chrome',
      use: { 
        ...devices['Desktop Chrome'],
        channel: 'chrome',
      },
    },
    {
      name: 'edge',
      use: { 
        ...devices['Desktop Edge'],
        channel: 'msedge',
      },
    },
  ],
});
