import { expect, mergeTests } from '@playwright/test'

import { workspace, sample, instrument } from '../fixtures'

const test = mergeTests(workspace, sample, instrument)

test.describe('sample batch ops', () => {
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
  test('import sample batch', async ({ page, freshBatch, sampleBrowser, acquisitionsTab }) => {
    await freshBatch.browserRow.click()
    await acquisitionsTab.open()
    await acquisitionsTab.filter('01/01/2020 00:00 - 01/01/2030 00:00')
    await acquisitionsTab.select(2)
    await acquisitionsTab.process()
    const dialog = page.getByLabel('import spreadsheet sample data')
    // paste data
    await page.evaluate(() =>
      navigator.clipboard.writeText(
        `name	type	filter id	foo	bar
    test_blank_item	BLANK	ABC123	1	fizz
    test_sample_item	SAMPLE	XYZ456	2	fuzz
    `
      )
    )
    await dialog.press('Control+v')
    await dialog.getByLabel('process').click()
    const confirm = page.getByLabel('import samples')
    await confirm.getByLabel('import').click()
    await expect(sampleBrowser.content).toContainText(
      'test_sample_item1XYZ456test_blank_item2ABC123'
    )
  })
})
