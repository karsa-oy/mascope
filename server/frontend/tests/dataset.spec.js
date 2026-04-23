import { expect, mergeTests } from '@playwright/test'

import { dataset } from './fixtures'

const test = mergeTests(dataset)

test.describe('dataset ops', () => {
  test('create dataset', async ({ freshDataset, datasetSelector }) => {
    await expect(datasetSelector.dropdown).toContainText(freshDataset.name)
  })
  test('rename dataset', async ({ page, freshDataset, datasetMenu, datasetSelector }) => {
    // open dialog
    await datasetMenu.button.click()
    await datasetMenu.items.getByLabel('edit dataset').locator('a').click()
    // edit dataset
    const editedName = `${freshDataset.name} (edited)`
    const dialog = page.getByLabel('edit dataset')
    await dialog.getByLabel('name').fill('')
    await dialog.getByLabel('name').pressSequentially(editedName)
    await dialog.getByLabel('save').click()
    await expect(datasetSelector.dropdown).toHaveText(editedName)
  })
  test('delete dataset', async ({ page, freshDataset, datasetMenu, datasetSelector }) => {
    await datasetMenu.button.click()
    await datasetMenu.items.getByLabel('delete dataset').locator('a').click()
    const dialog = page.getByLabel('delete dataset')
    await dialog.getByLabel('delete').click()
    await expect(datasetSelector.dropdown).not.toContainText(freshDataset.name)
    await datasetSelector.dropdown.click()
    await expect(datasetSelector.items).not.toContainText(freshDataset.name)
  })
})
