import { default as base } from './app'
import * as fs from 'fs/promises'
import * as path from 'path'

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
  },
  acquisitionsTab: async ({ page }, use) => {
    const panel = page.locator('#acquisitions')
    const open = () => page.getByRole('tab', { name: 'Acquisitions' }).click({ delay: 100 })
    const datetime = page.locator('#range')
    const filter = async (range) => {
      await datetime.fill(range)
      await datetime.press('Enter')
    }
    const select = async (value) => {
      if (typeof value == 'string') {
        await panel
          .getByRole('row', { name: `Row Unselected ${value}` })
          .getByLabel('Row Unselected')
          .check()
      } else if (typeof value == 'number') {
        const indeces = [...Array(value).keys()]
        // eslint-disable-next-line no-unused-vars
        for (const i in indeces) {
          await panel
            .getByRole('row', { name: 'Row Unselected' })
            .first()
            .getByLabel('Row Unselected')
            .check()
        }
      } else {
        await panel
          .getByRole('row', { name: 'Row Unselected' })
          .first()
          .getByLabel('Row Unselected')
          .check()
      }
    }
    const unselect = (filename) =>
      panel
        .getByRole('row', { name: `Row Selected ${filename}` })
        .getByLabel('Row Selected')
        .uncheck()
    const process = () => panel.getByLabel('Process').click({ delay: 50 })
    await use({ open, filter, datetime, select, unselect, process })
  },
  measurementMode: async ({ page }, use) => {
    const active = () => page.locator('#measurement-mode').textContent().includes('active')
    const activate = () => page.locator('#start-measuring').click()
    const deactivate = () => page.locator('#stop-measuring').click()
    await use({ active, activate, deactivate })
  },
  // eslint-disable-next-line no-empty-pattern
  orbi: async ({ page }, use) => {
    const converterDir = path.resolve('../runtime/data/streams')
    const testfileDir = path.resolve('../runtime/data/testfiles')
    const testfile = (await fs.readdir(testfileDir)).find((file) =>
      file.split('_')[0].toLowerCase().includes('orbi')
    )
    const datetime = (await page.evaluate('new Date().toISOString()'))
      .replaceAll('-', '')
      .replace('T', '_')
      .replace(':', '')
      .split(':')[0]
    const filename = `KORBI2_${datetime}_MION2_DBrMe_MM_NG_500pgul_x_1ul_60-600mz.raw`
    const acquire = async () => {
      const sourcepath = path.join(testfileDir, testfile)
      const targetpath = path.join(converterDir, filename)
      await fs.copyFile(sourcepath, targetpath)
      return { sourcepath, targetpath, filename }
    }
    await use({ converterDir, testfile, acquire })
    for (const file of await fs.readdir(converterDir)) {
      await fs.unlink(path.join(converterDir, file))
    }
  }
})
