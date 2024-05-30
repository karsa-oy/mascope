import { expect, mergeTests } from '@playwright/test'

import { workspace, sample, instrument } from '../fixtures'

const test = mergeTests(workspace, instrument, sample)

test.describe('sample item ops', () => {
  test('process sample item', async ({
    page,
    freshBatch,
    instrumentSelector,
    acquisitionsTab,
    sampleBrowser
  }) => {
    const testId = Math.random().toString(36).slice(2, 7)
    const name = `Test Sample ${testId} (basic)`
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
  test('acquire orbi file (convert & create)', async ({
    page,
    freshBatch,
    orbi,
    measurementMode,
    instrumentSelector,
    sampleBrowser
  }) => {
    // file conversion requires overriding timeouts
    const timeout = 10 * 60 * 1000
    test.setTimeout(timeout)
    const expectConversion = expect.configure({ timeout })
    // info
    const testId = Math.random().toString(36).slice(2, 7)
    const name = `Test Sample ${testId} (orbi)`
    // setup
    await instrumentSelector.select('KORBI2')
    await freshBatch.browserRow.click()
    await measurementMode.activate()
    // acquistion
    await orbi.acquire()
    const dialog = page.getByLabel('create a new sample item')
    await dialog.getByLabel('sample item name').fill(name)
    await dialog.locator('#item-type').click({ delay: 50 })
    await dialog.getByLabel('instrument background').click({ delay: 50 })
    await dialog.getByLabel('save').click()
    // validation
    await expectConversion(sampleBrowser.content).toContainText(name)
  })
})
