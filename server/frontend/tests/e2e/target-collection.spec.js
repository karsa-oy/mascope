import { test, expect, openWorkspace } from './fixtures'

/**
 * The collections table (MatchCollectionTable) only renders once a batch is
 * focused, so every collection test drills workspace -> dataset -> batch.
 */
async function openBatch(page, scratch, batchName) {
  await openWorkspace(page, scratch.workspace.workspace_name)
  await page.getByRole('row', { name: new RegExp(scratch.dataset.dataset_name) }).click()
  await page.getByRole('row', { name: new RegExp(batchName) }).click()
}

/** Seed a target collection in the scratch workspace through the API. */
async function seedCollection(api, scratch, name) {
  return (
    await api.post('/target/collections', {
      target_collection_name: name,
      workspace_id: scratch.workspace.workspace_id,
      target_collection_type: 'TARGETS'
    })
  ).data
}

test.describe('target collection ops', () => {
  test('create target collection', async ({ page, scratch }) => {
    const name = `e2e-created-tc-${scratch.id}`
    const batch = await scratch.createBatch(`e2e-batch-${scratch.id}`)
    await openBatch(page, scratch, batch.sample_batch_name)

    await page.getByRole('button', { name: 'Create target collection' }).click()
    const dialog = page.getByRole('dialog', { name: 'Create a new target collection' })
    await dialog.getByRole('textbox', { name: 'Name' }).fill(name)
    // Name, type and workspace scope are all required before submit enables.
    await dialog.getByRole('button', { name: 'TARGETS' }).click()
    // The scope combobox is only named by its placeholder while empty; when
    // opened from a workspace context it may arrive pre-filled.
    const scope = dialog.getByRole('combobox', { name: 'Select workspace scope' })
    if (await scope.count()) {
      await scope.click()
      await page.getByRole('option', { name: scratch.workspace.workspace_name }).click()
    }
    // The submit is labeled Save; a looser match would also catch the
    // "Create new" compound toggle inside the dialog.
    await dialog.getByRole('button', { name: 'Save', exact: true }).click()

    // A review step follows; confirming assigns the collection to the
    // focused batch, after which it appears in the collections table.
    const confirm = page.getByRole('alertdialog', { name: /Creating/ })
    await confirm.getByRole('button', { name: 'Create' }).dispatchEvent('click')
    await expect(page.getByText(name, { exact: true })).toBeVisible()
  })

  test('rename target collection', async ({ page, api, scratch }) => {
    const collection = await seedCollection(api, scratch, `e2e-tc-${scratch.id}`)
    const batch = await scratch.createBatch(`e2e-batch-${scratch.id}`, [
      collection.target_collection_id
    ])
    const renamed = `e2e-renamed-tc-${scratch.id}`
    await openBatch(page, scratch, batch.sample_batch_name)

    await page.getByText(collection.target_collection_name).click({ button: 'right' })
    // Menu items are labeled with the collection name, e.g. "Edit 'foo'".
    await page
      .getByRole('menuitem', { name: `Edit '${collection.target_collection_name}'` })
      .click()
    const dialog = page.getByRole('dialog', { name: /Edit/ })
    await dialog.getByRole('textbox', { name: 'Name' }).fill(renamed)
    await dialog.getByRole('button', { name: 'Save' }).click({ force: true })

    // Exact match: the success toast also contains the new name.
    await expect(page.getByText(renamed, { exact: true })).toBeVisible()
  })

  test('delete target collection', async ({ page, api, scratch }) => {
    const collection = await seedCollection(api, scratch, `e2e-tc-${scratch.id}`)
    const batch = await scratch.createBatch(`e2e-batch-${scratch.id}`, [
      collection.target_collection_id
    ])
    await openBatch(page, scratch, batch.sample_batch_name)

    // Exact match: success toasts also contain the collection name.
    const entry = page.getByText(collection.target_collection_name, { exact: true })
    await entry.click({ button: 'right' })
    await page
      .getByRole('menuitem', { name: `Delete '${collection.target_collection_name}'` })
      .click()
    // Deleting is a two-step flow: first a keep-or-remove-compounds chooser
    // (sane default pre-checked), then a final confirmation.
    const chooser = page.getByRole('dialog', { name: 'Delete target collection' })
    await chooser.getByRole('button', { name: 'Delete' }).click()
    const confirm = page.getByRole('alertdialog', { name: 'Delete collection' })
    await confirm.getByRole('button', { name: 'Delete' }).click()

    await expect(entry).toHaveCount(0)
  })
})
