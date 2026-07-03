import { test as base, expect } from '@playwright/test'

import { env } from './fixtures/env'

// Auth specs exercise the login UI itself, so start signed out.
const test = base.extend({})
test.use({ storageState: { cookies: [], origins: [] } })

// PrimeVue may place the id on the input or on a wrapper element.
const field = (page, id) => page.locator(`input#${id}, #${id} input`).first()

test.describe('authentication', () => {
  test('signs in through the login form', async ({ page }) => {
    await page.goto('/')
    await expect(page.getByText('Sign-in to Mascope')).toBeVisible()

    await field(page, 'login-email').fill(env.email)
    await field(page, 'login-password').fill(env.password)
    await page.getByRole('button', { name: 'Login' }).click()

    // Authenticated app shell replaces the login panel.
    await expect(page.locator('#app')).toBeVisible({ timeout: 30_000 })
    await expect(page.getByText('Sign-in to Mascope')).toBeHidden()
  })

  test('rejects a wrong password', async ({ page }) => {
    await page.goto('/')
    await expect(page.getByText('Sign-in to Mascope')).toBeVisible()

    await field(page, 'login-email').fill(env.email)
    await field(page, 'login-password').fill('definitely-not-the-password')
    await page.getByRole('button', { name: 'Login' }).click()

    // Still on the login screen, never into the app.
    await expect(page.getByText('Sign-in to Mascope')).toBeVisible()
    await expect(page.locator('#app')).toHaveCount(0)
  })
})
