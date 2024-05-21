import { expect, mergeTests } from '@playwright/test'

import { workspace, sample, instrument } from '../fixtures'

const test = mergeTests(workspace, instrument, sample)

test.describe('sample item ops', () => {
  test.beforeEach(async ({ page, context, browser }) => {
    await page.goto('http://localhost:8080/')
    if (browser.browserType() == 'chromium') {
      await context.grantPermissions(['clipboard-read', 'clipboard-write'])
    }
  })
  test('process sample item', async ({
    page,
    freshBatch,
    instrumentSelector,
    acquisitionsTab,
    sampleBrowser
  }) => {
    const testId = Math.random().toString(36).slice(2, 7)
    const name = `Test Sample ${testId}`
    await freshBatch.browserRow.click({ delay: 50 })
    await instrumentSelector.select('KLTOF1')
    await acquisitionsTab.open()
    await acquisitionsTab.filter('01/01/2020 00:00 - 01/01/2030 00:00')
    await acquisitionsTab.select()
    await acquisitionsTab.process()
    const dialog = page.getByLabel('create a new sample item')
    await dialog.getByLabel('sample item name').fill(name)
    await dialog.locator('#item-type').click({ delay: 50 })
    await dialog.getByLabel('instrument background').click({ delay: 50 })
    await dialog.getByLabel('save').click()
    await expect(sampleBrowser.content).toContainText(name)
  })
})
