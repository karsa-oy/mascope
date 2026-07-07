import { test, expect, openWorkspace } from './fixtures'

/** Drill into the scratch dataset so the batch browser is showing. */
async function openDataset(page, scratch) {
  await openWorkspace(page, scratch.workspace.workspace_name)
  await page.getByRole('row', { name: new RegExp(scratch.dataset.dataset_name) }).click()
  await expect(page.getByRole('button', { name: 'Create batch' })).toBeVisible()
}

test.describe('batch ops', () => {
  test('create batch', async ({ page, scratch }) => {
    const name = `e2e-created-batch-${scratch.id}`
    await openDataset(page, scratch)

    await page.getByRole('button', { name: 'Create batch' }).click()
    const dialog = page.getByRole('dialog', { name: /batch/i })
    await dialog.getByRole('textbox', { name: 'Name' }).fill(name)
    await dialog.getByRole('button', { name: /Create|Save/ }).click()

    await expect(page.getByRole('row', { name: new RegExp(name) })).toBeVisible()
  })

  test('rename batch', async ({ page, scratch }) => {
    const batch = await scratch.createBatch(`e2e-batch-${scratch.id}`)
    const renamed = `e2e-renamed-batch-${scratch.id}`
    await openDataset(page, scratch)

    await page
      .getByRole('row', { name: new RegExp(batch.sample_batch_name) })
      .click({ button: 'right' })
    await page.getByRole('menuitem', { name: 'Edit batch', exact: true }).click()
    const dialog = page.getByRole('dialog', { name: /Edit.*batch/i })
    await dialog.getByRole('textbox', { name: 'Name' }).fill(renamed)
    // The batch dialog title re-renders live with the typed name and keeps
    // shifting layout, so position-based clicks (even forced) are racy -
    // dispatch the click event directly instead.
    await dialog.getByRole('button', { name: 'Save' }).dispatchEvent('click')

    await expect(page.getByRole('row', { name: new RegExp(renamed) })).toBeVisible()
  })

  test('delete batch', async ({ page, scratch }) => {
    const batch = await scratch.createBatch(`e2e-batch-${scratch.id}`)
    await openDataset(page, scratch)

    const row = page.getByRole('row', { name: new RegExp(batch.sample_batch_name) })
    await row.click({ button: 'right' })
    await page.getByRole('menuitem', { name: 'Delete batch' }).click()
    // The confirmation renders as an alertdialog, unlike the edit dialogs.
    const dialog = page.getByRole('alertdialog', { name: /Delete.*batch/i })
    await dialog.getByRole('button', { name: 'Delete' }).click({ force: true })

    await expect(row).toHaveCount(0)
  })
})
