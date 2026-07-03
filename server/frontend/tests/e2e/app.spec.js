import { test, expect, env } from './fixtures'

test.describe('app shell (demo data)', () => {
  test('renders the dashboard for a signed-in user', async ({ page }) => {
    // Fixture already waited for #app; assert the core landmarks are up.
    await expect(page.locator('#app')).toBeVisible()
    await expect(page.locator('#instrument-selector')).toBeAttached()
  })

  test('identifies the signed-in user via the API cookie', async ({ api }) => {
    const me = await api.get('/users/me')
    expect(me.email).toBe(env.email)
  })

  test('serves the seeded demo data through the API', async ({ api }) => {
    const batches = await api.get('/sample/batches')
    expect(Array.isArray(batches)).toBeTruthy()
    expect(batches.length, 'demo dataset should contain at least one batch').toBeGreaterThan(0)

    const instruments = await api.get('/instruments')
    expect(Array.isArray(instruments)).toBeTruthy()
  })
})
