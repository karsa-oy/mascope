import { ref, reactive } from 'vue'

import { api } from '@/api'

import { useApp } from '@/stores'

export const useMzFit = ({ unmount } = { unmount: false }) => {
  const app = useApp()

  //  TODO_configuration default calibration parameters
  const DEFAULT_MZ_CALIBRATION_PARAMS = {
    match_score_min: 0,
    isotope_abundance_min: 0.15,
    peak_intensity_min: 0, //1000,
    refine_window: 100
  }

  // state
  const active = ref(null)
  const status = ref(null)
  const current = ref(null)
  const error = ref(null)
  const stats = ref(null)
  const mzCalibrationParams = reactive({ ...DEFAULT_MZ_CALIBRATION_PARAMS })

  async function load(sample) {
    current.value =
      (await api.http.get(`/calibration/mz_calibration`, {
        params: {
          sample_item_id: sample.sample_item_id
        },
        use: 'read',
        type: 'read_mz_calibration'
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
    const { sample_item_id } = sample ?? active.value
    await api.http.post(`/calibration/mz_fit`, mzCalibrationParams, {
      params: { sample_item_id },
      use: 'process',
      type: 'mz_fit'
    })
  }

  async function apply(sample) {
    const { filename } = sample ?? active.value
    await api.http.post(
      `/calibration/mz_apply`,
      { fit: current.value },
      {
        params: { filename },
        use: 'process',
        type: 'apply_mz_fit'
      }
    )
  }

  const handler = app.ui.notification.on('calibration_mz_fit', (payload) => {
    status.value = payload?.status
    if (payload?.status === 'success') {
      current.value = payload?.data?.fit
      stats.value = payload?.data?.stats
    }
    if (payload?.status === 'error') {
      error.value = payload?.message
      // Critical errors prevent further steps
      stats.value = null
      current.value = null
    }
    if (payload?.status === 'warning') {
      error.value = payload?.message
      // Allow further steps if stats are available
      current.value = payload?.error?.detail?.data?.fit
      stats.value = payload?.error?.detail?.data?.stats
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
    mzCalibrationParams,
    // actions
    load,
    unload,
    compute,
    apply
  })
}
