import { test, expect, env } from './fixtures'

test.describe('app shell (demo data)', () => {
  test('renders the dashboard for a signed-in user', async ({ page }) => {
    // The fixture waited for the instrument selector; assert the login
    // screen is gone and the dashboard landmarks are up.
    await expect(page.getByText('Sign-in to Mascope')).toHaveCount(0)
    await expect(page.locator('#instrument-selector')).toBeAttached()
  })

  test('identifies the signed-in user via the API cookie', async ({ api }) => {
    const me = (await api.get('/users/me')).data
    expect(me.email).toBe(env.email)
  })

  test('serves the seeded demo data through the API', async ({ api }) => {
    // Walk the data hierarchy: workspaces -> datasets -> batches.
    // List endpoints respond with a { message, results, data } wrapper.
    const workspaces = (await api.get('/workspaces')).data
    expect(workspaces.length, 'demo dataset should contain a workspace').toBeGreaterThan(0)

    const datasets = (await api.get(`/workspaces/${workspaces[0].workspace_id}/datasets`)).data
    expect(datasets.length, 'demo workspace should contain a dataset').toBeGreaterThan(0)

    const batches = (await api.get(`/sample/batches?dataset_id=${datasets[0].dataset_id}`)).data
    expect(batches.length, 'demo dataset should contain a sample batch').toBeGreaterThan(0)
  })
})
