import { test as base } from '@playwright/test'

export default base.extend({
  instrumentSelector: async ({ page }, use) => {
    const dropdown = page.locator('#instrument-selector')
    const open = async () => await dropdown.click({ delay: 100 })
    const items = page.locator('#instrument-selector ~ .p-select-overlay').locator('ul')
    const select = async (instrument) => {
      await dropdown.click({ delay: 50 })
      await items.getByLabel(instrument).click({ delay: 50 })
    }
    await use({ dropdown, items, open, select })
  }
})
