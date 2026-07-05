import { describe, it, expect, vi, beforeEach } from 'vitest'
import { nextTick } from 'vue'
import { createPinia, setActivePinia } from 'pinia'

// The store registers a socket listener at setup; a stub is all it needs.
vi.mock('@/api', () => ({
  api: {
    socket: { on: vi.fn(), id: 'test-sid' },
    http: { get: vi.fn(), post: vi.fn() }
  }
}))

import { useNotification } from '@/stores/ui/notification'

describe('notification store', () => {
  let store

  beforeEach(() => {
    setActivePinia(createPinia())
    vi.useFakeTimers()
    store = useNotification()
  })

  it('displays and logs a plain notification', () => {
    store.push({ type: 'info', status: 'success', message: 'saved' })

    expect(store.latest.message).toBe('saved')
    expect(store.log).toHaveLength(1)
  })

  it('counts warnings and errors until the badge is cleared', () => {
    store.push({ type: 'x', status: 'warning', message: 'w' })
    store.push({ type: 'x', status: 'error', message: 'e' })

    expect(store.recentWarnings).toBe(1)
    expect(store.recentErrors).toBe(1)

    store.clearRecentBadge()

    expect(store.recentWarnings).toBe(0)
    expect(store.recentErrors).toBe(0)
  })

  it('tracks a pending process without logging it', () => {
    store.push({
      type: 'mz_fit',
      status: 'pending',
      process_id: 'p1',
      message: 'working',
      progress: 10
    })

    expect(store.progress).toHaveLength(1)
    expect(store.log).toHaveLength(0)
  })

  it('completes a process: removed from progress, logged and displayed', () => {
    store.push({ type: 'mz_fit', status: 'pending', process_id: 'p1', progress: 10 })
    store.push({ type: 'mz_fit', status: 'success', process_id: 'p1', message: 'done' })

    expect(store.progress).toHaveLength(0)
    expect(store.log).toHaveLength(1)
    expect(store.latest.message).toBe('done')
  })

  it('logs but does not display child process notifications', () => {
    store.push({
      type: 'mz_fit',
      status: 'success',
      process_id: 'child',
      parent_id: 'root',
      message: 'child done'
    })

    expect(store.log).toHaveLength(1)
    expect(store.latest).toBe(null)
  })

  it('expires an idle pending process after its timeout', () => {
    store.push({ type: 'mz_fit', status: 'pending', process_id: 'p1', progress: 10 })
    expect(store.progress).toHaveLength(1)

    vi.advanceTimersByTime(31 * 1000)

    expect(store.progress).toHaveLength(0)
  })

  it('triggers watchers for matching types and the wildcard', async () => {
    const onMzFit = vi.fn()
    const onAnything = vi.fn()
    store.on('mz_fit', onMzFit)
    store.on('*', onAnything)

    store.push({ type: 'mz_fit', status: 'success', message: 'done' })
    await nextTick()

    expect(onMzFit).toHaveBeenCalledOnce()
    expect(onAnything).toHaveBeenCalledOnce()

    store.push({ type: 'other', status: 'success', message: 'x' })
    await nextTick()

    expect(onMzFit).toHaveBeenCalledOnce()
    expect(onAnything).toHaveBeenCalledTimes(2)
  })

  it('caps the log at the retention limit', () => {
    for (let i = 0; i < 260; i++) {
      store.push({ type: 'x', status: 'success', message: `m${i}` })
    }

    expect(store.log).toHaveLength(250)
    expect(store.log[0].message).toBe('m259')
  })
})
