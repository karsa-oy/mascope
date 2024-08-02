import { ref, reactive } from 'vue'

import { api } from '@/api'

import { useApp } from '@/stores'

export const useMzFit = ({ unmount } = { unmount: false }) => {
  const app = useApp()

  // state
  const active = ref(null)
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

  async function load(sample) {
    current.value =
      (await api.request.read({
        method: 'getMzCalibration',
        body: { sample_item_id: sample.sample_item_id }
      })) ?? current.value
    active.value = sample
  }

  async function unload() {
    active.value = null
    status.value = null
    current.value = null
    error.value = null
    stats.value = null
  }

  async function compute(sample) {
    await unload()
    const { sample_item_id, sample_item_name } = sample ?? active.value
    await api.request.process({
      method: 'calibrationMzFit',
      body: {
        sampleId: sample_item_id,
        sampleName: sample_item_name,
        body: params
      }
    })
  }

  async function apply(sample) {
    const { filename } = sample ?? active.value
    await api.request.process({
      method: 'calibrationMzApply',
      body: {
        fit: current.value,
        filename
      }
    })
  }

  const handler = app.ui.notification.on('calibration_mz_fit', (payload) => {
    status.value = payload?.status
    if (payload?.status === 'success') {
      current.value = payload?.data?.fit
      stats.value = payload?.data?.stats
    }
    if (payload?.status === 'error') {
      error.value = payload?.message
      stats.value = payload?.data?.stats
    }
  })
  if (unmount) {
    handler.unmount()
  }

  return reactive({
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
    apply
  })
}
