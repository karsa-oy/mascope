import { expect } from '@playwright/test'

import { default as base } from './app'

export default base.extend({
  datasetSelector: async ({ page }, use) => {
    const dropdown = page.locator('#dataset-selector')
    const open = async () => await dropdown.click({ delay: 100 })
    const items = page.locator('#dataset-selector ~ .p-select-overlay').locator('ul')
    const select = async (dataset) => {
      await dropdown.click({ delay: 50 })
      await items.getByLabel(dataset).click({ delay: 50 })
    }
    use({ dropdown, items, open, select })
  },
  datasetMenu: async ({ page }, use) => {
    const button = page.getByLabel('dataset menu')
    const open = async () => await button.click({ delay: 100 })
    const items = page.locator('#dataset-menu')
    use({ button, items, open })
  },
  freshDataset: async ({ page, datasetMenu, datasetSelector }, use) => {
    // record first dataset
    await datasetSelector.open()
    const firstDataset = await datasetSelector.items.locator('li').first().textContent()
    // new dataset identifiers
    const testId = Math.random().toString(36).slice(2, 7)
    const name = `Test Dataset ${testId}`
    // open creation dialog
    await datasetMenu.open()
    await datasetMenu.items.getByLabel('create dataset').locator('a').click({ delay: 200 })
    const createDialog = page.getByLabel('create a new dataset')
    // create dataset
    await createDialog.getByLabel('name').fill(name)
    await createDialog.getByLabel('create').click()
    await expect(datasetSelector.dropdown).toContainText(name)
    const select = () => datasetSelector.select(name)
    // expose api
    await use({ name, select })
    // cleanup
    let shouldDelete = true
    const selected = (await datasetSelector.dropdown.textContent()).includes(name)
    if (!selected) {
      await datasetSelector.open()
      const exists = (await datasetSelector.items.textContent()).includes(name)
      if (!exists) {
        shouldDelete = false
      } else {
        await datasetSelector.items.getByLabel(name).click({ delay: 50 })
      }
    }
    if (shouldDelete) {
      await datasetMenu.open()
      await datasetMenu.items.getByLabel('delete dataset').locator('a').click({ delay: 200 })
      const deleteDialog = page.getByLabel('delete dataset')
      await deleteDialog.getByLabel('delete').click({ delay: 200 })
      await expect(datasetSelector.dropdown).toContainText(firstDataset)
    }
    // validate
    await datasetSelector.open()
    await expect(datasetSelector.items).not.toContainText(name)
  }
})
