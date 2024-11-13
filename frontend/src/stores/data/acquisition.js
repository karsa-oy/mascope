import { ref, reactive, computed, watch, watchEffect } from 'vue'
import { defineStore } from 'pinia'

import { api } from '@/api'

import { useSample } from './sample'
import { useInstrument } from './instrument'

import { useUi } from '../ui'

export const useAcquisition = defineStore('app.data.acquisition', () => {
  const ui = useUi()
  const sample = useSample()
  const instrument = useInstrument()

  const mode = ref(false)
  const list = ref([])
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

  const time = reactive({
    mode: 'Last 24 hours',
    range: {
      min: null,
      max: null
    }
  })
  const days = computed(() =>
    time.mode == 'range' ? null : time.mode == 'Last 24 hours' ? 1 : Number(time.mode.split(' ')[1])
  )
  watchEffect(() => {
    if (time.range.min || time.range.max) {
      time.mode = 'range'
    } else {
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

  ui.notification.on('instrument_conversion', ({ process_id, data, status }) => {
    if (mode.value) {
      // conversion started
      if (process_id !== pending.conversion) {
        pending.conversion = process_id
        if (orbi.value) {
          pending.filename = data?.filename
        }
      } else {
        if (status !== 'pending') {
          pending.conversion = null
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

  return {
    // state
    mode,
    list,
    pending,
    ready,
    time,
    mzCalibration,
    // actions
    load
  }
})
