import { default as base } from './workspace'

export default base.extend({
  sampleBrowser: async ({ page }, use) => {
    const panel = page.locator('.k-browser', { hasText: 'samples' })
    const header = panel.locator('.p-panel-header')
    const content = panel.locator('.p-panel-content')
    const button = panel.getByLabel('create batch')
    const createBatch = () => button.click({ delay: 200, force: true })
    await use({ panel, header, content, createBatch })
  },
  existingBatch: async ({ page }, use) => {
    const name = '20230726_stability'
    const browserRow = page.getByRole('cell', { name })
    await use({ name, browserRow })
  },
  // eslint-disable-next-line no-unused-vars
  freshBatch: async ({ page, freshWorkspace, sampleBrowser }, use) => {
    const testId = Math.random().toString(36).slice(2, 7)
    const name = `Test Batch ${testId}`
    // open dialog
    await sampleBrowser.createBatch()
    // create batch
    const dialog = page.getByLabel('create a new sample batch')
    await dialog.getByLabel('name').fill(name)
    await dialog.getByLabel('save').click({ delay: 200 })
    // wait for creation
    const browserRow = await page.getByRole('cell', { name })
    // api
    await use({ name, browserRow })
  }
})
