import { test as base, expect } from '@playwright/test'

import { env } from './env'

/**
 * Base test for the hermetic e2e suite.
 *
 * - `page` arrives already signed in (cookie state from setup/auth.setup.js,
 *   wired via storageState in playwright.config.js) and navigated to the app.
 * - `api` is an authenticated helper for seeding and cleaning up state through
 *   the REST API. Prefer it over UI interactions for anything that is setup
 *   rather than the behavior under test: API seeding is fast and deterministic,
 *   UI seeding is where the flakiness lives.
 */
export const test = base.extend({
  page: async ({ page }, use) => {
    await page.goto('/')
    // The app shell is up once the workspace has loaded past the spinner.
    await page.locator('#app').waitFor({ timeout: 30_000 })
    await use(page)
  },

  api: async ({ playwright }, use) => {
    const context = await playwright.request.newContext({
      baseURL: env.apiURL,
      storageState: env.storageStatePath
    })

    const raise = async (response, method, path) => {
      if (!response.ok()) {
        throw new Error(`${method} ${path} -> ${response.status()}: ${await response.text()}`)
      }
      return response
    }

    const api = {
      /** GET an /api path and return parsed JSON. */
      get: async (path) => (await raise(await context.get(`/api${path}`), 'GET', path)).json(),
      /** POST JSON to an /api path and return parsed JSON (null for empty bodies). */
      post: async (path, data) => {
        const response = await raise(await context.post(`/api${path}`, { data }), 'POST', path)
        const text = await response.text()
        return text ? JSON.parse(text) : null
      },
      /** PATCH JSON to an /api path. */
      patch: async (path, data) =>
        (await raise(await context.patch(`/api${path}`, { data }), 'PATCH', path)).json(),
      /** DELETE an /api path (used by cleanup hooks). */
      delete: async (path) => raise(await context.delete(`/api${path}`), 'DELETE', path)
    }

    await use(api)
    await context.dispose()
  }
})

export { expect, env }
