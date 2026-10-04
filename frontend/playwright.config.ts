import { defineConfig } from '@playwright/test'
const dev = process.env.TRACEREVIEW_E2E_MODE === 'dev'

export default defineConfig({
  testDir: './e2e', timeout: 40000, expect: { timeout: 10000 },
  fullyParallel: false, workers: 1, retries: 0,
  outputDir: '../output/playwright/results',
  reporter: [['list'], ['html', { outputFolder: '../output/playwright/report', open: 'never' }]],
  use: {
    baseURL: dev ? 'http://127.0.0.1:5174' : 'http://127.0.0.1:8001',
    viewport: { width: 1440, height: 900 },
    trace: 'retain-on-failure', screenshot: 'only-on-failure',
  },
  webServer: [
    { command: 'uv run --locked python ../scripts/e2e_server.py', url: 'http://127.0.0.1:8001/api/session/', reuseExistingServer: false, timeout: 60000 },
    ...(dev ? [{ command: 'npm run dev -- --port 5174', url: 'http://127.0.0.1:5174', reuseExistingServer: false, timeout: 60000,
      env: { TRACEREVIEW_API_URL: 'http://127.0.0.1:8001' } }] : []),
  ],
})
