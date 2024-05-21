import { test as base, expect } from '@playwright/test'

export default base.extend({
  workspaceSelector: async ({ page }, use) => {
    const dropdown = page.locator('#workspace-selector')
    const open = async () => await dropdown.click({ delay: 100 })
    const items = page.locator('#workspace-selector ~ .p-select-overlay').locator('ul')
    const select = async (workspace) => {
      await dropdown.click({ delay: 50 })
      await items.getByLabel(workspace).click({ delay: 50 })
    }
    use({ dropdown, items, open, select })
  },
  workspaceMenu: async ({ page }, use) => {
    const button = page.getByLabel('workspace menu')
    const open = async () => await button.click({ delay: 100 })
    const items = page.locator('#workspace-menu')
    use({ button, items, open })
  },
  freshWorkspace: async ({ page, workspaceMenu, workspaceSelector }, use) => {
    // record first workspace
    await workspaceSelector.open()
    const firstWorkspace = await workspaceSelector.items.locator('li').first().textContent()
    // new workspace identifiers
    const testId = Math.random().toString(36).slice(2, 7)
    const name = `Test Workspace ${testId}`
    // open creation dialog
    await workspaceMenu.open()
    await workspaceMenu.items.getByLabel('create workspace').locator('a').click({ delay: 200 })
    const createDialog = page.getByLabel('create a new workspace')
    // create workspace
    await createDialog.getByLabel('name').fill(name)
    await createDialog.getByLabel('create').click()
    await expect(workspaceSelector.dropdown).toContainText(name)
    const select = () => workspaceSelector.select(name)
    // expose api
    await use({ name, select })
    // cleanup
    let shouldDelete = true
    const selected = (await workspaceSelector.dropdown.textContent()).includes(name)
    if (!selected) {
      await workspaceSelector.open()
      const exists = (await workspaceSelector.items.textContent()).includes(name)
      if (!exists) {
        shouldDelete = false
      } else {
        await workspaceSelector.items.getByLabel(name).click({ delay: 50 })
      }
    }
    if (shouldDelete) {
      await workspaceMenu.open()
      await workspaceMenu.items.getByLabel('delete workspace').locator('a').click({ delay: 200 })
      const deleteDialog = page.getByLabel('delete workspace')
      await deleteDialog.getByLabel('delete').click({ delay: 200 })
      await expect(workspaceSelector.dropdown).toContainText(firstWorkspace)
    }
    // validate
    await workspaceSelector.open()
    await expect(workspaceSelector.items).not.toContainText(name)
  }
})
