import { expect, mergeTests } from '@playwright/test'

import { workspace } from './fixtures'

const test = mergeTests(workspace)

test.describe('workspace ops', () => {
  test('create workspace', async ({ freshWorkspace, workspaceSelector }) => {
    await expect(workspaceSelector.dropdown).toContainText(freshWorkspace.name)
  })
  test('rename workspace', async ({ page, freshWorkspace, workspaceMenu, workspaceSelector }) => {
    // open dialog
    await workspaceMenu.button.click()
    await workspaceMenu.items.getByLabel('edit workspace').locator('a').click()
    // edit workspace
    const editedName = `${freshWorkspace.name} (edited)`
    const dialog = page.getByLabel('edit workspace')
    await dialog.getByLabel('name').fill('')
    await dialog.getByLabel('name').pressSequentially(editedName)
    await dialog.getByLabel('save').click()
    await expect(workspaceSelector.dropdown).toHaveText(editedName)
  })
  test('delete workspace', async ({ page, freshWorkspace, workspaceMenu, workspaceSelector }) => {
    await workspaceMenu.button.click()
    await workspaceMenu.items.getByLabel('delete workspace').locator('a').click()
    const dialog = page.getByLabel('delete workspace')
    await dialog.getByLabel('delete').click()
    await expect(workspaceSelector.dropdown).not.toContainText(freshWorkspace.name)
    await workspaceSelector.dropdown.click()
    await expect(workspaceSelector.items).not.toContainText(freshWorkspace.name)
  })
})
