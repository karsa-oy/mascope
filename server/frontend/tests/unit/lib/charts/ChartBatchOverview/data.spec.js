import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { nextTick, reactive } from 'vue'
import { createPinia, setActivePinia } from 'pinia'

// The store talks to the API and the app store at setup; both are stubbed.
vi.mock('@/api', () => ({
  api: {
    socket: { on: vi.fn(), off: vi.fn(), id: 'test-sid' },
    http: { get: vi.fn(), post: vi.fn() }
  }
}))

const mockApp = reactive({
  ui: {
    chart: { register: vi.fn() },
    darkmode: { active: false }
  },
  data: {
    batch: { focusedId: 'batch-1' },
    sample: {
      list: [
        {
          sample_item_id: 's1',
          sample_item_name: 'Sample 1',
          datetime: '2026-01-01T10:00:00',
          tic: 1000,
          length: 2
        },
        {
          sample_item_id: 's2',
          sample_item_name: 'Sample 2',
          datetime: '2026-01-01T11:00:00',
          tic: 2000,
          length: 2
        },
        {
          sample_item_id: 's3',
          sample_item_name: 'Sample 3',
          datetime: '2026-01-01T12:00:00',
          tic: 3000,
          length: 2
        }
      ]
    },
    match: {
      ion: {
        selectedIds: [],
        list: [{ target_ion_id: 'ion-1' }, { target_ion_id: 'ion-2' }]
      }
    },
    ionization: { mechanism: { filteredIds: ['mech-1'] } }
  }
})

vi.mock('@/stores', () => ({
  useApp: () => mockApp
}))

import { api } from '@/api'
import { useChartData } from '@/lib/charts/ChartBatchOverview/data'

/** Series record as returned by POST /match/records/ion/series */
const seriesRecord = (ionId, series, extra = {}) => ({
  target_compound_id: `compound-${ionId}`,
  target_compound_name: `Compound ${ionId}`,
  target_compound_formula: 'CH4',
  target_ion_id: ionId,
  target_ion_formula: 'CH5+',
  ionization_mechanism_id: 'mech-1',
  ionization_mechanism: 'H3O+',
  match_series: series,
  ...extra
})

const flushAsync = async () => {
  // let the selection watcher run, awaited fetches resolve, and computeds settle
  await nextTick()
  await vi.waitFor(() => expect(useChartData().pending).toBe(false))
  await nextTick()
}

describe('chart.batch.overview data store', () => {
  let store

  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
    mockApp.data.match.ion.selectedIds = []
    store = useChartData()
  })

  afterEach(() => {
    // stop this instance's watchers so they don't react to the shared
    // mockApp in later tests
    store.$dispose()
  })

  it('requests series scoped by batch id, not per-sample id lists', async () => {
    api.http.post.mockResolvedValue([
      seriesRecord('ion-1', {
        sample_item_ids: ['s1'],
        sample_peak_intensity_sums: [5],
        match_categories: [1]
      })
    ])

    mockApp.data.match.ion.selectedIds = ['ion-1']
    await flushAsync()

    expect(api.http.post).toHaveBeenCalledTimes(1)
    const [url, body] = api.http.post.mock.calls[0]
    expect(url).toBe('/match/records/ion/series')
    expect(body).toEqual({ sample_batch_id: 'batch-1', target_ion_ids: ['ion-1'] })
  })

  it('loads ions in chunks of 100 per request', async () => {
    api.http.post.mockResolvedValue([])

    mockApp.data.match.ion.selectedIds = Array.from({ length: 250 }, (_, i) => `ion-${i}`)
    await flushAsync()

    expect(api.http.post).toHaveBeenCalledTimes(3)
    expect(api.http.post.mock.calls[0][1].target_ion_ids).toHaveLength(100)
    expect(api.http.post.mock.calls[2][1].target_ion_ids).toHaveLength(50)
  })

  it('builds one trace per matched ion plus TIC, with y aligned to samples', async () => {
    api.http.post.mockResolvedValue([
      seriesRecord('ion-1', {
        sample_item_ids: ['s1', 's3'],
        sample_peak_intensity_sums: [5, 7],
        match_categories: [1, 2]
      }),
      // no matches: must not produce a trace
      seriesRecord('ion-2', {
        sample_item_ids: [],
        sample_peak_intensity_sums: [],
        match_categories: []
      })
    ])

    mockApp.data.match.ion.selectedIds = ['ion-1', 'ion-2']
    await flushAsync()

    expect(store.traces).toHaveLength(2) // ion-1 + TIC
    const [ionTrace, ticTrace] = store.traces
    expect(ionTrace.y).toEqual([5, null, 7]) // s2 unmatched -> null
    expect(ionTrace.matchData.target_ion_id).toBe('ion-1')
    expect(ionTrace.marker.symbol).toBe('square') // max category 2
    expect(ticTrace.name).toBe('TIC')
    expect(ticTrace.y).toEqual([1000, 2000, 3000])
  })

  it('shares the per-sample customdata and text arrays across ion traces', async () => {
    api.http.post.mockResolvedValue([
      seriesRecord('ion-1', {
        sample_item_ids: ['s1'],
        sample_peak_intensity_sums: [5],
        match_categories: [1]
      }),
      seriesRecord('ion-2', {
        sample_item_ids: ['s2'],
        sample_peak_intensity_sums: [6],
        match_categories: [1]
      })
    ])

    mockApp.data.match.ion.selectedIds = ['ion-1', 'ion-2']
    await flushAsync()

    const [a, b] = store.traces
    expect(a.customdata).toBe(b.customdata)
    expect(a.text).toBe(b.text)
    expect(a.y).not.toBe(b.y)
  })

  it('drops traces for ions filtered out by ionization mechanism', async () => {
    api.http.post.mockResolvedValue([
      seriesRecord(
        'ion-1',
        {
          sample_item_ids: ['s1'],
          sample_peak_intensity_sums: [5],
          match_categories: [1]
        },
        { ionization_mechanism_id: 'mech-other' }
      )
    ])

    mockApp.data.match.ion.selectedIds = ['ion-1']
    await flushAsync()

    expect(store.traces).toHaveLength(1) // TIC only
    expect(store.traces[0].name).toBe('TIC')
  })

  it('removes a deleted sample from every series and drops emptied ions', async () => {
    api.http.post.mockResolvedValue([
      seriesRecord('ion-1', {
        sample_item_ids: ['s1', 's2'],
        sample_peak_intensity_sums: [5, 6],
        match_categories: [1, 1]
      }),
      seriesRecord('ion-2', {
        sample_item_ids: ['s2'],
        sample_peak_intensity_sums: [9],
        match_categories: [1]
      })
    ])

    mockApp.data.match.ion.selectedIds = ['ion-1', 'ion-2']
    await flushAsync()
    expect(store.traces).toHaveLength(3) // ion-1, ion-2, TIC

    // simulate the sample_match_deleted socket event
    const deletedHandler = api.socket.on.mock.calls.find(
      ([event]) => event === 'sample_match_deleted'
    )[1]
    deletedHandler({ record_id: 's2' })
    await nextTick()

    expect(store.traces).toHaveLength(2) // ion-2 emptied out; ion-1 + TIC remain
    expect(store.traces[0].y).toEqual([5, null, null])
  })
})
