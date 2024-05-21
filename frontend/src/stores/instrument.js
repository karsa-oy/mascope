import { ref, reactive, computed, watch, watchEffect } from 'vue'
import { defineStore } from 'pinia'

import { api } from '@/api'

import { useNotification } from './notification'
import { useMzFit } from './mzFit'
import { useSampleStore } from './sample'
import { useAppStore } from './app'

export const useInstrumentStore = defineStore('instrument', () => {
  const appStore = useAppStore()
  const notification = useNotification()

  const active = ref(null)
  const acquisitions = ref([])
  const pending = reactive({
    filename: null,
    sampleItem: null,
    acquisition: null,
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
    const appStore = useAppStore()
    if (appStore.mode?.measuring) {
      time.mode = 'Last 24 hours'
    }
  })

  const mzCalibration = ref(null)
  const orbi = computed(() => active.value?.instrument.toLowerCase().includes('orbi'))
  // instrument

  watch(active, async (next, prev) => {
    if (prev) await unload(prev.instrument)
    load(next.instrument)
  })

  async function load(instrument) {
    api.emit('subscribe', instrument)
    await loadMzCalibration()
    await loadAcquisitions()
  }

  async function unload(instrument) {
    if (!instrument) return
    api.emit('unsubscribe', instrument)
    mzCalibration.value = null
    acquisitions.value = null
    await resetAcquisitionStatus()
  }

  // acquisitions

  watch(time, loadAcquisitions)

  function loadAcquisitions() {
    if (time.mode.startsWith('Last')) {
      loadAcquisitionsRecent(days.value)
    } else if (time.mode == 'range') {
      const [min, max] = time.range
      if (min && max) {
        loadAcquisitionsRange({
          min,
          max
        })
      }
    }
  }

  async function loadAcquisitionsRange(range) {
    const sampleFiles = await (
      await api.request.read({
        method: 'getAllSampleFiles',
        body: {
          datetime_min: range.min.toISOString(),
          datetime_max: range.max.toISOString(),
          instrument: active.value.instrument,
          sort: 'datetime_utc',
          order: 'asc'
        }
      })
    )?.data
    if (sampleFiles) {
      acquisitions.value = sampleFiles
    }
  }

  async function loadAcquisitionsRecent(days = 7) {
    const recent = (
      await api.request.read({
        method: 'getRecentSampleFiles',
        body: {
          instrument: active.value.instrument,
          sort: 'datetime_utc',
          order: 'asc',
          days
        }
      })
    )?.data
    if (recent) {
      acquisitions.value = recent
    }
  }

  async function resetAcquisitionStatus() {
    pending.filename = null
    const mzFit = useMzFit()
    mzFit.status = null
  }

  notification.on('instrument_acquisition', ({ process_id, data, status }) => {
    if (appStore.mode.measuring) {
      // acquisition started
      if (process_id !== pending.acquisition) {
        resetAcquisitionStatus()
        pending.acquisition = process_id
        pending.filename = data?.filename
      } else {
        if (status !== 'pending') {
          pending.acquisition = null
        }
      }
    }
  })()

  notification.on('instrument_conversion', ({ process_id, data, status }) => {
    if (appStore.mode.measuring) {
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
    loadAcquisitions()
    if (pending.sampleItem) {
      const sampleStore = useSampleStore()
      await sampleStore.process(pending.sampleItem)
      pending.sampleItem = null
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
          instrument: active.value.instrument
        }
      })
    )?.data
    if (!lastMzCalibration) return
    mzCalibration.value = lastMzCalibration
  }

  return {
    // state
    active,
    acquisitions,
    pending,
    ready,
    time,
    mzCalibration,
    // actions
    load,
    unload,
    loadAcquisitions,
    resetAcquisitionStatus
  }
})
