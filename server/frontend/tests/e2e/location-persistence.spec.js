import { test, expect, openWorkspace } from './fixtures'

/**
 * Copy the "link to this view" and return the URL the app put on the clipboard.
 * The shared link is built from the live store state, so it doubles as a probe
 * for where the app currently is - more robust than reaching into PrimeVue
 * table internals.
 */
async function copyLink(page) {
  const share = page.getByRole('button', { name: 'Copy link to this view' })
  if (!(await share.isVisible())) return ''
  await share.click()
  return page.evaluate(() => navigator.clipboard.readText())
}

/** Drill into the scratch dataset and focus a batch. */
async function focusBatch(page, scratch, batch) {
  await openWorkspace(page, scratch.workspace.workspace_name)
  await page.getByRole('row', { name: new RegExp(scratch.dataset.dataset_name) }).click()
  await page.getByRole('row', { name: new RegExp(batch.sample_batch_name) }).click()
  await expect(page.getByRole('button', { name: 'Copy link to this view' })).toBeVisible()
}

test.describe('UI location persistence', () => {
  test('restores the focused batch after a full reload', async ({ page, scratch }) => {
    const batch = await scratch.createBatch(`e2e-persist-${scratch.id}`)
    await focusBatch(page, scratch, batch)

    const before = await copyLink(page)
    expect(before).toContain(`b=${batch.sample_batch_id}`)

    // Full reload, as an auto-update restart or a manual refresh would do.
    await page.reload()
    await page.locator('#instrument-selector').waitFor({ state: 'attached', timeout: 30_000 })

    // The chain restores asynchronously; the shared link reflects the live
    // selection, so poll it until the batch is focused again.
    await expect
      .poll(() => copyLink(page), { timeout: 20_000 })
      .toContain(`b=${batch.sample_batch_id}`)
  })

  test('opens a shared link at the same location', async ({ page, scratch }) => {
    const batch = await scratch.createBatch(`e2e-share-${scratch.id}`)
    await focusBatch(page, scratch, batch)

    const url = await copyLink(page)
    expect(url).toContain(`b=${batch.sample_batch_id}`)

    // Clear the personal snapshot so only the URL can drive the restore.
    await page.evaluate(() => window.localStorage.clear())

    await page.goto(url)
    await page.locator('#instrument-selector').waitFor({ state: 'attached', timeout: 30_000 })

    await expect
      .poll(() => copyLink(page), { timeout: 20_000 })
      .toContain(`b=${batch.sample_batch_id}`)

    // Mirroring keeps the address bar in sync with the restored location, so
    // the query reflects the batch rather than being stripped.
    await expect
      .poll(() => page.evaluate(() => window.location.search))
      .toContain(`b=${batch.sample_batch_id}`)
  })

  test('mirrors the focused batch into the address bar', async ({ page, scratch }) => {
    const batch = await scratch.createBatch(`e2e-mirror-${scratch.id}`)
    await focusBatch(page, scratch, batch)

    // Focusing a batch is reflected in the URL without any explicit share action.
    await expect
      .poll(() => page.evaluate(() => window.location.search), { timeout: 10_000 })
      .toContain(`b=${batch.sample_batch_id}`)
  })
})
