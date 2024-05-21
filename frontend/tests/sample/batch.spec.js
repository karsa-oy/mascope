import { expect, mergeTests } from '@playwright/test'

import { workspace, sample } from '../fixtures'

const test = mergeTests(workspace, sample)

test.describe('sample batch ops', () => {
  test.beforeEach(async ({ page, context, browser }) => {
    await page.goto('http://localhost:8080/')
    if (browser.browserType() == 'chromium') {
      await context.grantPermissions(['clipboard-read', 'clipboard-write'])
    }
  })
  test('create sample batch', async ({ freshBatch }) => {
    // validate
    await expect(freshBatch.browserRow).toContainText(freshBatch.name)
  })
  test('rename sample batch', async ({ page, freshBatch, sampleBrowser }) => {
    await freshBatch.browserRow.click({ button: 'right' })
    await page.getByLabel('edit batch').first().click({ delay: 50 })
    const dialog = page.getByLabel('edit sample batch')
    const editedName = `${freshBatch.name} (edited)`
    await dialog.getByLabel('name').fill('')
    await dialog.getByLabel('name').pressSequentially(editedName)
    await dialog.getByLabel('save').click()
    // validate
    await expect(sampleBrowser.content).toContainText(editedName)
  })
  test('delete sample batch', async ({ page, freshBatch, sampleBrowser }) => {
    await freshBatch.browserRow.click({ button: 'right' })
    await page.getByLabel('delete batch').click()
    const dialog = await page.getByLabel('delete sample batch')
    await dialog.getByLabel('delete').click()
    // validate
    await expect(sampleBrowser.content).not.toContainText(freshBatch.name)
  })
})
