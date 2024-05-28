// @ts-check
import { defineConfig, devices } from '@playwright/test'

/**
 * Read environment variables from file.
 * https://github.com/motdotla/dotenv
 */
// require('dotenv').config();

/**
 * @see https://playwright.dev/docs/test-configuration
 */
export default defineConfig({
  testDir: './tests',
  timeout: 1 * 30 * 1000, // ms
  // expect: {
  //   timeout: 30 * 1000
  // },
  // // some settings differ in CI/CD
  workers: 1, // process.env.CI ? 1 : undefined,
  retries: 2, // process.env.CI ? 2 : 0,
  forbidOnly: !!process.env.CI,
  use: {
    trace: 'on-all-retries',
    permissions: ['clipboard-read', 'clipboard-write']
  },
  reporter: [['list'], ['html']],
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] }
    },
    {
      name: 'webkit',
      use: { ...devices['Desktop Safari'] }
    },
    {
      name: 'firefox',
      use: { ...devices['Desktop Firefox'] }
    }
  ],
  reportSlowTests: {
    max: 5,
    threshold: 20 * 1000 // ms
  }
})
