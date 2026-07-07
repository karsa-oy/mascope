import { describe, it, expect, beforeEach, vi } from 'vitest'
import { ref, nextTick } from 'vue'
import { createPinia, setActivePinia } from 'pinia'

// selection.js only touches the socket API through the `subscribe` option,
// which these tests do not exercise; a stub keeps the import graph happy.
vi.mock('@/api', () => ({
  api: {
    socket: { addSubscription: vi.fn(), removeSubscription: vi.fn() }
  }
}))

import { useSelection } from '@/lib/store/selection'

// Drive the refocus machinery the loader would run after a data sync.
const refocus = (sel) => sel.prepRefocus()()

describe('useSelection persistence', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    localStorage.clear()
  })

  it('persists a single focused id as a JSON array', async () => {
    const records = ref([{ sample_batch_id: 'a' }, { sample_batch_id: 'b' }])
    const sel = useSelection('batch', 'sample_batch_id', () => records.value, { persist: true })

    sel.focus({ sample_batch_id: 'b' })
    await nextTick()

    expect(JSON.parse(localStorage.getItem('module[batch]'))).toEqual(['b'])
  })

  it('restores a single focused id after a reload', () => {
    localStorage.setItem('module[batch]', JSON.stringify(['b']))
    const records = ref([{ sample_batch_id: 'a' }, { sample_batch_id: 'b' }])
    const sel = useSelection('batch', 'sample_batch_id', () => records.value, { persist: true })

    refocus(sel)

    expect(sel.focusedId.value).toBe('b')
  })

  it('persists and restores a multi-select set', async () => {
    localStorage.clear()
    const records = ref([
      { sample_item_id: 's1' },
      { sample_item_id: 's2' },
      { sample_item_id: 's3' }
    ])
    const sel = useSelection('sample', 'sample_item_id', () => records.value, {
      mode: 'multiple',
      persist: true
    })

    sel.select({ sample_item_id: 's1' }, { sample_item_id: 's3' })
    await nextTick()
    expect(JSON.parse(localStorage.getItem('module[sample]'))).toEqual(['s1', 's3'])

    // fresh page: new pinia (empty selection), storage survives
    setActivePinia(createPinia())
    const records2 = ref([
      { sample_item_id: 's1' },
      { sample_item_id: 's2' },
      { sample_item_id: 's3' }
    ])
    const sel2 = useSelection('sample', 'sample_item_id', () => records2.value, {
      mode: 'multiple',
      persist: true
    })
    refocus(sel2)

    expect(sel2.selectedIds.value.sort()).toEqual(['s1', 's3'])
  })

  it('drops stored ids that no longer exist and clears the entry', () => {
    localStorage.setItem('module[batch]', JSON.stringify(['gone']))
    const records = ref([{ sample_batch_id: 'a' }, { sample_batch_id: 'b' }])
    const sel = useSelection('batch', 'sample_batch_id', () => records.value, { persist: true })

    refocus(sel)

    expect(sel.focusedId.value).toBe(null)
    expect(localStorage.getItem('module[batch]')).toBe(null)
  })

  it('keeps the entry while records are empty (deps not yet met)', () => {
    localStorage.setItem('module[batch]', JSON.stringify(['b']))
    const records = ref([])
    const sel = useSelection('batch', 'sample_batch_id', () => records.value, { persist: true })

    refocus(sel)

    expect(sel.focusedId.value).toBe(null)
    // entry preserved so it can restore once data arrives
    expect(JSON.parse(localStorage.getItem('module[batch]'))).toEqual(['b'])
  })

  it('tolerates a legacy bare-id string from earlier persistence', () => {
    localStorage.setItem('module[batch]', 'b') // pre-array format
    const records = ref([{ sample_batch_id: 'a' }, { sample_batch_id: 'b' }])
    const sel = useSelection('batch', 'sample_batch_id', () => records.value, { persist: true })

    refocus(sel)

    expect(sel.focusedId.value).toBe('b')
  })

  it('clears storage when the selection is emptied', async () => {
    const records = ref([{ sample_batch_id: 'a' }, { sample_batch_id: 'b' }])
    const sel = useSelection('batch', 'sample_batch_id', () => records.value, { persist: true })

    sel.focus({ sample_batch_id: 'b' })
    await nextTick()
    expect(localStorage.getItem('module[batch]')).not.toBe(null)

    sel.unfocus()
    await nextTick()
    expect(localStorage.getItem('module[batch]')).toBe(null)
  })

  it('does not clear stored state during a deps-unmet refocus', async () => {
    // Regression: a refocus while records are empty (parent not focused yet)
    // reassigns the selection to a fresh empty array. Persisting must not treat
    // that empty -> empty churn as a real change and wipe the stored id before
    // it can be restored once the data arrives.
    localStorage.setItem('module[batch]', JSON.stringify(['b']))
    const records = ref([])
    const sel = useSelection('batch', 'sample_batch_id', () => records.value, { persist: true })

    refocus(sel)
    await nextTick()

    expect(JSON.parse(localStorage.getItem('module[batch]'))).toEqual(['b'])
  })

  it('does not write storage when persist is disabled', async () => {
    const records = ref([{ sample_batch_id: 'a' }, { sample_batch_id: 'b' }])
    const sel = useSelection('batch', 'sample_batch_id', () => records.value, {})

    sel.focus({ sample_batch_id: 'b' })
    await nextTick()

    expect(localStorage.getItem('module[batch]')).toBe(null)
  })
})
