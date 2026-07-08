import { describe, it, expect, vi, beforeEach } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'

import { docUrl, DOCS_BASE, useHelp } from '@/stores/ui/help'

describe('help docUrl', () => {
  it('builds a link under the docs base', () => {
    expect(docUrl('how-it-works/matching/')).toBe('/docs/how-it-works/matching/')
  })

  it('defaults to the docs home', () => {
    expect(docUrl()).toBe('/docs/')
    expect(DOCS_BASE).toBe('/docs/')
  })

  it('strips leading slashes so the path is always relative to the base', () => {
    expect(docUrl('/concepts/')).toBe('/docs/concepts/')
    expect(docUrl('///reference/')).toBe('/docs/reference/')
  })
})

describe('help currentMessage', () => {
  let store

  beforeEach(async () => {
    setActivePinia(createPinia())
    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ matching: '<p>matching body</p>' })
    })
    store = useHelp()
    await store.loadContent()
  })

  it('renders a docs-sourced card as title + snippet body', () => {
    store.current = { helpKey: 'matching', title: 'Match view' }
    expect(store.currentMessage).toBe('<h1>Match view</h1><p>matching body</p>')
  })

  it('prefers an inline message when present (legacy cards)', () => {
    store.current = { message: '<h1>Inline</h1>' }
    expect(store.currentMessage).toBe('<h1>Inline</h1>')
  })

  it('falls back to the title alone when the snippet is missing (e.g. dev)', () => {
    store.current = { helpKey: 'absent', title: 'Match view' }
    expect(store.currentMessage).toBe('<h1>Match view</h1>')
  })
})
