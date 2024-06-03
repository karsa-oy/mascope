import { ref, reactive } from 'vue'
import { defineStore } from 'pinia'

import { api } from '@/api'

import { useNotification } from './notification'
import { useSampleStore } from './sample'
import { useAppStore } from './app'

export const useMzFit = defineStore('mzFit', () => {
  const notification = useNotification()

  // state
  const status = ref(null)
  const current = ref(null)
  const error = ref(null)
  const stats = ref(null)
  const params = reactive({
    match_score_min: 0,
    min_isotope_abundance: 0.15,
    peak_intensity_min: 0, //1000,
    refine_window: 100
  })

  // data loading
  async function load(sample) {
    // reset if previous calibration loaded
    const calibration = await api.request.read({
      method: 'getMzCalibration',
      body: {
        sample_item_id: sample.sample_item_id
      }
    })
    if (!calibration) return
    current.value = calibration
  }

  async function unload() {
    current.value = null
    error.value = null
    stats.value = null
  }

  async function compute(sample) {
    await api.request.process({
      method: 'calibrationMzFit',
      body: {
        sampleId: sample.sample_item_id,
        sampleName: sample.sample_item_name,
        body: params
      }
    })
  }

  async function apply(filename) {
    await api.request.process({
      method: 'calibrationMzApply',
      body: {
        fit: current.value,
        filename
      }
    })
  }

  async function calibrate() {
    const sampleStore = useSampleStore()
    if (sampleStore.active) {
      await api.request.read({
        method: 'calibrationMzCalibrateSample',
        body: {
          sampleId: sampleStore.active.sample_item_id,
          sampleName: sampleStore.active.sample_item_name,
          body: params
        }
      })
    } else {
      const appStore = useAppStore()
      if (appStore.mode.measuring) {
        setTimeout(() => calibrate(), 1000)
      }
    }
  }

  notification.on('calibration_mz_fit', ({ status, data, error }) => {
    if (status === 'success') {
      current.value = data?.fit
      stats.value = data?.stats
    }
    if (status === 'error') {
      error.value = error?.detail?.data?.error
      stats.value = error?.detail?.data?.stats
    }
  })()

  return {
    // state
    status,
    current,
    error,
    stats,
    params,
    // actions
    load,
    unload,
    compute,
    apply,
    calibrate
  }
})
