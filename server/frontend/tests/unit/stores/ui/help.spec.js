import { describe, it, expect } from 'vitest'

import { docUrl, DOCS_BASE } from '@/stores/ui/help'

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
