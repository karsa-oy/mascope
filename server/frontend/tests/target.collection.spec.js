import { expect, mergeTests } from '@playwright/test'

import { dataset, sample, target } from './fixtures'

const test = mergeTests(dataset, sample, target)

test.describe('target collection ops', () => {
  test('create target collection', async ({ freshCollection }) => {
    // validate
    await freshCollection.browserRow.click({ delay: 50 })
    await expect(freshCollection.browserRow).toContainText(freshCollection.name)
  })
  test('rename target collection', async ({ page, freshCollection, targetBrowser }) => {
    await freshCollection.browserRow.click({ button: 'right' })
    await page.getByLabel('edit collection').first().click({ delay: 50 })
    const dialog = page.getByLabel('edit target collection')
    const editedName = `${freshCollection.name} (edited)`
    await dialog.getByLabel('name').first().fill('')
    await dialog.getByLabel('name').first().pressSequentially(editedName)
    await dialog.getByLabel('save').click()
    // validate
    await expect(targetBrowser.content).toContainText(editedName)
  })
  test('delete target collection', async ({ page, freshCollection, targetBrowser }) => {
    await freshCollection.browserRow.click({ button: 'right' })
    await page.getByLabel('delete collection').click()
    const dialog = page.getByLabel('delete target collection')
    await dialog.getByLabel('Delete', { exact: true }).click({ delay: 50 })
    const confirm = page.getByLabel('delete collection')
    await confirm.getByLabel('delete').click({ delay: 50 })
    // validate
    await expect(targetBrowser.content).not.toContainText(freshCollection.name)
  })
})
