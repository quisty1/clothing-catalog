import { defineConfig } from '@playwright/test';
export default defineConfig({
  testDir: './tests',
  use: {baseURL: process.env.E2E_BASE_URL || 'http://127.0.0.1:3000',
    launchOptions: process.env.PLAYWRIGHT_CHROME_PATH ? {executablePath:process.env.PLAYWRIGHT_CHROME_PATH} : {}},
  webServer: process.env.E2E_BASE_URL ? undefined : {
    command: 'npm run dev', url: 'http://127.0.0.1:3000', reuseExistingServer: !process.env.CI, timeout:120000
  },
  reporter: 'list'
});
