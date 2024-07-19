import { ref, reactive, computed, watch, watchEffect } from 'vue'
import { defineStore } from 'pinia'

import { api } from '@/api'

import { useData } from './data'
import { useNotification } from './notification'

export const useAcquisition = defineStore('app.acquisition', () => {
  const notification = useNotification()
  const data = useData()

  const mode = ref(false)
  const list = ref([])
  const pending = reactive({
    filename: null,
    sample: null,
    measurement: null,
    conversion: null
  })
  const ready = reactive({
    filename: null
  })

  const time = reactive({
    mode: 'Last 24 hours',
    range: null
  })
  const days = computed(() =>
    time.mode == 'range' ? null : time.mode == 'Last 24 hours' ? 1 : Number(time.mode.split(' ')[1])
  )
  watchEffect(() => {
    const range = time.range
    if (range && range[0] && range[1]) {
      time.mode = 'range'
    }
  })
  watchEffect(() => {
    if (mode.value) {
      time.mode = 'Last 24 hours'
    }
  })

  const mzCalibration = ref(null)
  const orbi = computed(() => data.instrument.focused.toLowerCase().includes('orbi'))
  // instrument

  watch(
    computed(() => data.instrument.focused),
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
      const [min, max] = time.range
      if (min && max) {
        await loadRange({
          min,
          max
        })
      }
    }
  }

  async function loadRange(range) {
    const sampleFiles = await (
      await api.request.read({
        method: 'getAllSampleFiles',
        body: {
          datetime_min: range.min.toISOString(),
          datetime_max: range.max.toISOString(),
          instrument: data.instrument.focused,
          sort: 'datetime_utc',
          order: 'asc'
        }
      })
    )?.data
    if (sampleFiles) {
      list.value = sampleFiles
    }
  }

  async function loadRecent(days = 7) {
    const recent = (
      await api.request.read({
        method: 'getRecentSampleFiles',
        body: {
          instrument: data.instrument.focused,
          sort: 'datetime_utc',
          order: 'asc',
          days
        }
      })
    )?.data
    if (recent) {
      list.value = recent
    }
  }

  notification.on('instrument_acquisition', ({ process_id, data, status }) => {
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
  })()

  notification.on('instrument_conversion', ({ process_id, data, status }) => {
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
  })()

  // measurement mode
  notification.on('create_sample_file', async () => {
    load()
    if (pending.sample) {
      await data.sample.process(pending.sample)
      pending.sample = null
    } else {
      ready.filename = pending.filename
    }
  })()

  // mz calibration

  async function loadMzCalibration() {
    const lastMzCalibration = (
      await api.request.read({
        method: 'getMzCalibration',
        body: {
          instrument: data.instrument.focused?.instrument
        }
      })
    )?.data
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
