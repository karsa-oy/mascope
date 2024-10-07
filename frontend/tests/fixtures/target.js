import { default as base } from './workspace'

export default base.extend({
  targetBrowser: async ({ page }, use) => {
    const panel = page.locator('.browser', { hasText: 'targets' })
    const header = panel.locator('.p-panel-header')
    const content = panel.locator('.p-panel-content')
    const button = panel.getByLabel('create collection')
    const createCollection = () => button.click({ delay: 200 })
    await use({ panel, header, content, createCollection })
  },
  existingCollection: async ({ page }, use) => {
    const name = 'Explosives targets'
    const browserRow = await page.getByRole('cell', { name })
    use({ name, browserRow })
  },
  freshCollection: async ({ page, freshBatch, targetBrowser }, use) => {
    const testId = Math.random().toString(36).slice(2, 7)
    const name = `Test Collection ${testId}`
    // open batch
    await freshBatch.browserRow.click()
    // open dialog
    await targetBrowser.createCollection()
    // create collection
    const dialog = page.getByLabel('create a new target collection')
    await dialog.getByLabel('name').first().fill(name)
    // add a compound
    await page.getByLabel('All', { exact: true }).click()
    await page
      .getByRole('row', { name: 'Row Unselected Water H2O' })
      .getByLabel('Row Unselected')
      .check()
    await dialog.getByLabel('save').click()
    // wait for creation
    const browserRow = await page.getByRole('cell', { name })
    // api
    await use({ name, browserRow })
  }
})
