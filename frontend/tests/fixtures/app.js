import { test as base } from '@playwright/test'

base.beforeEach(async ({ page }) => {
  // spoof time
  const testtime = randomDate('3000-01-02', '3999-12-30')
  await page.addInitScript(`{
    const offset = ${testtime} - Date.now()
    const realtime = Date.now

    Date = class extends Date {
      constructor(...args) {
        if (args.length === 0) {
          super(realtime() + offset)
        } else {
          super(...args)
        }
      }
    }
    Date.now = () => realtime() + offset
  }`)
  // go to the app
  await page.goto('http://localhost:8080/')
})

export default base

function randomDate(from, to) {
  const start = new Date(from)
  const end = new Date(to)
  return new Date(start.getTime() + Math.random() * (end.getTime() - start.getTime())).valueOf()
}
