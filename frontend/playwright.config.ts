import { defineConfig, devices } from '@playwright/test'

// Isolated stack on non-default ports so e2e never touches a dev database:
// offline engine, demo geopolitics, synthetic forecast band, fast steps.
const API = 'http://127.0.0.1:8100'
const WEB = 'http://127.0.0.1:5174'

export default defineConfig({
  testDir: './tests/e2e',
  timeout: 90_000,
  fullyParallel: false,
  workers: 1,
  reporter: [['list']],
  use: { baseURL: WEB, trace: 'retain-on-failure' },
  projects: [{ name: 'chromium', use: { ...devices['Desktop Chrome'] } }],
  webServer: [
    {
      command: 'uv run --no-sync python -m geoalpha.cli serve --port 8100',
      cwd: '../backend',
      url: `${API}/api/health`,
      timeout: 120_000,
      reuseExistingServer: false,
      env: {
        GEOALPHA_ENGINE: 'fake',
        GEOALPHA_GEO_PROVIDER: 'fixture',
        GEOALPHA_FAKE_FORECAST: '1',
        GEOALPHA_FAKE_STEP_DELAY_S: '0.4',
        GEOALPHA_DATA_DIR: `./data-e2e-${Date.now()}`,
      },
    },
    {
      command: 'npx vite --host 127.0.0.1 --port 5174 --strictPort',
      url: WEB,
      timeout: 120_000,
      reuseExistingServer: false,
      env: { GEOALPHA_API_TARGET: API },
    },
  ],
})
