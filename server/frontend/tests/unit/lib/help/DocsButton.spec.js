import { describe, it, expect, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import PrimeVue from 'primevue/config'

// DocsButton only reaches into the aggregate store for a help-card pt object;
// stub it so the test does not pull in the whole store tree (and its socket/API
// side effects).
vi.mock('@/stores', () => ({
  useApp: () => ({ ui: { help: { bottom_end: () => ({}) } } })
}))

import DocsButton from '@/lib/help/DocsButton.vue'

const noop = {}

describe('DocsButton', () => {
  it('renders an anchor that opens the docs site in a new tab', () => {
    const wrapper = mount(DocsButton, {
      global: {
        plugins: [PrimeVue],
        directives: { tooltip: noop, ripple: noop }
      }
    })

    const link = wrapper.get('a')
    expect(link.attributes('href')).toBe('/docs/')
    expect(link.attributes('target')).toBe('_blank')
    expect(link.attributes('rel')).toContain('noopener')
  })
})
