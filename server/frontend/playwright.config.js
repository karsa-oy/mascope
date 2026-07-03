// @ts-check
import { defineConfig, devices } from '@playwright/test'

import { env } from './tests/e2e/fixtures/env.js'

/**
 * End-to-end tests live under tests/e2e/: hermetic, run against any live
 * stack, by default the demo stack (docker-compose.demo.yaml at
 * http://localhost:8080), which is seeded with the published demo dataset
 * and the demo login. Deterministic, CI-eligible. `npm run test:e2e`
 *
 * Environment overrides (see tests/e2e/fixtures/env.js):
 *   MASCOPE_E2E_BASE_URL   frontend origin       (default http://localhost:8080)
 *   MASCOPE_E2E_API_URL    API origin            (default = base URL)
 *   MASCOPE_E2E_EMAIL      login email           (default demo@mascope.app)
 *   MASCOPE_E2E_PASSWORD   login password        (default mascope-demo)
 *   MASCOPE_E2E_STACK=demo have Playwright start docker-compose.demo.yaml itself
 *
 * @see https://playwright.dev/docs/test-configuration
 */
export default defineConfig({
  testDir: './tests',
  timeout: 30 * 1000, // ms
  workers: 1,
  forbidOnly: !!process.env.CI,
  use: {
    trace: 'retain-on-failure',
    permissions: ['clipboard-read', 'clipboard-write']
  },
  reporter: [['list'], ['html', { open: 'never' }]],
  projects: [
    // --- Hermetic e2e (demo-stack) suite ---
    {
      name: 'e2e-setup',
      testDir: './tests/e2e/setup',
      testMatch: /.*\.setup\.js/,
      use: { baseURL: env.baseURL }
    },
    {
      name: 'e2e',
      testDir: './tests/e2e',
      testIgnore: /setup\//,
      dependencies: ['e2e-setup'],
      retries: process.env.CI ? 1 : 0,
      use: {
        ...devices['Desktop Chrome'],
        baseURL: env.baseURL,
        storageState: env.storageStatePath
      }
    },
    {
      name: 'e2e-firefox',
      testDir: './tests/e2e',
      testIgnore: /setup\//,
      dependencies: ['e2e-setup'],
      use: {
        ...devices['Desktop Firefox'],
        baseURL: env.baseURL,
        storageState: env.storageStatePath
      }
    },
    {
      name: 'e2e-webkit',
      testDir: './tests/e2e',
      testIgnore: /setup\//,
      dependencies: ['e2e-setup'],
      use: {
        ...devices['Desktop Safari'],
        baseURL: env.baseURL,
        storageState: env.storageStatePath
      }
    }
  ],
  // Opt-in: let Playwright bring the demo stack up itself. First run downloads
  // the demo bundle (~150 MB), hence the generous timeout. Otherwise the stack
  // is expected to already be running (docker compose -f docker-compose.demo.yaml up).
  webServer:
    process.env.MASCOPE_E2E_STACK === 'demo'
      ? {
          command: 'docker compose -f ../../docker-compose.demo.yaml up',
          url: env.baseURL,
          reuseExistingServer: true,
          timeout: 15 * 60 * 1000
        }
      : undefined,
  reportSlowTests: {
    max: 5,
    threshold: 20 * 1000 // ms
  }
})
