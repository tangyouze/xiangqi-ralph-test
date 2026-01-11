import { defineConfig, devices } from '@playwright/test';

export default defineConfig({
  testDir: './e2e',
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 1 : undefined,
  reporter: 'html',
  use: {
    baseURL: 'http://localhost:6701',
    trace: 'on-first-retry',
  },
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
  ],
  webServer: [
    {
      command: 'cd ../backend && source .venv/bin/activate && uvicorn main:app --host 0.0.0.0 --port 6702',
      url: 'http://localhost:6702/health',
      reuseExistingServer: !process.env.CI,
      timeout: 30000,
    },
    {
      command: 'cd ../backend && source .venv/bin/activate && uvicorn jieqi.api.app:app --host 0.0.0.0 --port 6703',
      url: 'http://localhost:6703/health',
      reuseExistingServer: !process.env.CI,
      timeout: 30000,
    },
    {
      command: 'npm run dev -- --port 6701',
      url: 'http://localhost:6701',
      reuseExistingServer: !process.env.CI,
      timeout: 30000,
    },
  ],
});
