import { ref, reactive, computed, watch, watchEffect } from 'vue'
import { defineStore } from 'pinia'

import { api } from '@/api'
import { runtime } from '@/lib/runtime'

import { useSample } from './sample'
import { useInstrument } from './instrument'

import { useUi } from '../ui'

export const useAcquisition = defineStore('app.data.acquisition', () => {
  const ui = useUi()
  const sample = useSample()
  const instrument = useInstrument()

  const mode = ref(false)
  const list = ref([])
  const selected = ref([])
  const focused = computed(() => {
    if (selected.value.length === 1) {
      return selected.value[0]
    } else {
      return null
    }
  })
  const multiselected = computed(() => selected.value.length > 1)
  const unfocus = () => {
    selected.value = []
  }
  const pending = reactive({
    filename: null,
    sample: null,
    method_file: null,
    measurement: null,
    conversion: null
  })
  const ready = reactive({
    filename: null
  })

  const time = reactive(initTime())
  const days = computed(() =>
    time.mode == 'range' ? null : time.mode == 'Last 24 hours' ? 1 : Number(time.mode.split(' ')[1])
  )
  watchEffect(() => {
    if (time.range.min || time.range.max) {
      time.mode = 'range'
    } else if (time.mode == 'range') {
      time.mode = 'Last 24 hours'
    }
  })
  watchEffect(() => {
    if (mode.value) {
      time.mode = 'Last 24 hours'
    }
  })
  // Clear or reset notifications when mode changes
  watchEffect(() => {
    if (!mode.value) {
      ui.notification.clearLatest()
    }
  })
  watch(time, () => unfocus())

  const mzCalibration = ref(null)
  const orbi = computed(() => instrument.focused.instrument.toLowerCase().includes('orbi'))

  // instrument

  watch(
    computed(() => instrument.focused?.instrument),
    async () => {
      mzCalibration.value = null
      pending.filename = null
      await loadMzCalibration()
      await load()
    }
  )

  watch(
    () => instrument.focused,
    (next, prev) => {
      // clear selection
      unfocus()
      // update socket subscriptions
      if (prev) {
        api.socket.emit('unsubscribe', prev.instrument)
      }
      if (next) {
        api.socket.emit('subscribe', next.instrument)
      }
    }
  )

  // acquisitions

  watch(time, load)

  async function load() {
    if (time.mode.startsWith('Last')) {
      await loadRecent(days.value)
    } else if (time.mode == 'range') {
      await loadRange(time.range)
    }
  }

  async function loadRange(range) {
    const sampleFiles = await api.http.get(`/sample/files`, {
      params: {
        datetime_min: range.min?.toISOString(),
        datetime_max: range.max?.toISOString(),
        instrument: instrument.focused?.instrument,
        sort: 'datetime_utc',
        order: 'asc'
      },
      use: 'read',
      type: 'load_sample_file_range'
    })
    if (sampleFiles) {
      list.value = sampleFiles
    }
  }

  async function loadRecent(days = 7) {
    const recent = await api.http.get(`/sample/files/recent`, {
      params: {
        instrument: instrument.focused?.instrument,
        sort: 'datetime_utc',
        order: 'asc',
        days
      },
      use: 'read',
      type: 'load_recent_sample_files'
    })
    if (recent) {
      list.value = recent
    }
  }

  api.socket.on('acquisitions_reload', () => {
    load()
  })

  ui.notification.on('instrument_acquisition', ({ process_id, data, status }) => {
    if (mode.value) {
      // acquisition started
      if (process_id !== pending.measurement) {
        pending.filename = null
        pending.measurement = process_id
        pending.filename = data?.filename
      } else {
        if (status !== 'pending') {
          pending.measurement = null
        }
      }
    }
  })

  // measurement mode
  ui.notification.on('create_sample_file', async () => {
    load()
    if (pending.sample) {
      await sample.process({
        sample: pending.sample,
        method_file: pending.method_file
      })
      pending.sample = null
    } else {
      ready.filename = pending.filename
    }
  })

  // mz calibration

  async function loadMzCalibration() {
    const lastMzCalibration = await api.http.get(`/calibration/mz_calibration`, {
      params: {
        instrument: instrument.focused?.instrument
      },
      use: 'read',
      type: 'load_mz_calibration'
    })
    if (!lastMzCalibration) return
    mzCalibration.value = lastMzCalibration
  }

  const resetFilters = () => {
    selected.value = []
    time.mode = initTime().mode
    time.range = initTime().range
  }

  return {
    // state
    mode,
    list,
    selected,
    focused,
    multiselected,
    unfocus,
    pending,
    ready,
    time,
    mzCalibration,
    // actions
    load,
    resetFilters
  }
})

const toDate = (iso) => (iso ? new Date(iso) : null)

function initTime() {
  const configured = runtime.config.acquisition_filter
  if (configured) {
    if (typeof configured == 'string') {
      return {
        mode: configured,
        range: {
          min: null,
          max: null
        }
      }
    } else if (typeof configured == 'object') {
      return {
        mode: 'range',
        range: {
          min: toDate(configured.min),
          max: toDate(configured.max)
        }
      }
    }
  } else {
    return {
      mode: 'Last 24 hours',
      range: {
        min: null,
        max: null
      }
    }
  }
}
