import { ref, computed } from 'vue'
import { defineStore } from 'pinia'

import { api } from '@/api'

import { useSampleStore } from './sample'
import { useInstrumentStore } from './instrument'
import { useNotificationStore } from './notification'
import { useBatchStore } from './batch'

export const useCalibrationStore = defineStore('calibration', () => {
  // state

  const active = ref(null)
  const calibrationStatus = ref(null)
  const mzFit = ref(null)
  const mzFitError = ref(null)
  const mzFitStats = ref(null)
  const paramMatchScoreMin = ref(0)
  const paramMinIsotopeAbundance = ref(0.1)
  const paramMinPeakIntensity = ref(1000)
  const paramRefineWindow = ref(100)

  // getters

  const params = computed(() => ({
    match_score_min: paramMatchScoreMin.value,
    refine_window: paramRefineWindow.value,
    peak_intensity_min: paramMinPeakIntensity.value,
    isotope_abundance_min: paramMinIsotopeAbundance.value
  }))

  // data loading
  async function load(sample) {
    // reset if previous calibration loaded
    if (active.value) {
      await unload()
    }
    mzFit.value = await getSampleMzCalibration(sample)
  }

  async function unload() {
    mzFit.value = null
    mzFitError.value = null
    mzFitStats.value = null
  }

  // http client endpoints
  async function getSampleMzCalibration({ sample_item_id }) {
    return await api.request({
      httpMethod: 'getMzCalibration',
      requestData: {
        sample_item_id
      },
      errorMessage: `Failed to get sample mz calibration.`
    })
  }

  async function calibrationMzFit(requestData) {
    await api.request({
      httpMethod: 'calibrationMzFit',
      requestData: requestData,
      errorMessage: `Failed to calibrate mz fit of sample ${requestData.sampleName}.`
    })
  }

  async function calibrationMzApply(requestData) {
    await api.request({
      httpMethod: 'calibrationMzApply',
      requestData: requestData,
      errorMessage: `Failed to apply mz calibration for sample file ${requestData.sample_filename}.`
    })
  }

  async function calibrationMzCalibrateSample() {
    const sampleStore = useSampleStore()
    const sampleActive = sampleStore.active
    if (sampleActive) {
      const sampleId = sampleActive.sample_item_id
      const sampleName = sampleActive.sample_item_name
      const body = params.value
      await api.request({
        httpMethod: 'calibrationMzCalibrateSample',
        requestData: { sampleId, sampleName, body },
        errorMessage: `Failed to m/z calibrate sample ${sampleName}.`
      })
    } else {
      const instrumentStore = useInstrumentStore()
      if (!instrumentStore.scenthoundModeActive) return
      setTimeout(() => calibrationMzCalibrateSample(), 1000)
    }
  }

  // backend notifications
  // mz_fit
  async function onCalibrationMzFitStarted(data) {
    const notificationStore = useNotificationStore()
    notificationStore.onCalibrationStarted(data)
  }
  async function onCalibrationMzFitProgress(data) {
    const notificationStore = useNotificationStore()
    notificationStore.onCalibrationProgress(data)
  }
  async function onCalibrationMzFitFinished(data) {
    mzFit.value = data.fit
    mzFitError.value = data.error
    mzFitStats.value = data.stats
    const notificationStore = useNotificationStore()
    notificationStore.onCalibrationFinished(data)
  }
  async function onCalibrationMzFitFailed(data) {
    const notificationStore = useNotificationStore()
    notificationStore.onCalibrationFailed(data)
  }

  // mz_apply
  async function onCalibrationMzApplyStarted(data) {
    const notificationStore = useNotificationStore()
    notificationStore.onCalibrationStarted(data)
  }
  async function onCalibrationMzApplyFinished(data) {
    const notificationStore = useNotificationStore()
    if (data.autosampler_mode === true) {
      notificationStore.onCalibrationFinished(data)
    } else {
      await unload()
      const sampleStore = useSampleStore()
      await sampleStore.reload(sampleStore.active)
      const batchStore = useBatchStore()
      await batchStore.reload(null)
      notificationStore.onCalibrationFinished(data)
    }
  }

  // mz_calibrate_sample
  // TODO_notifications
  async function onCalibrationMzCalibrateSampleStarted(data) {
    calibrationStatus.value = data
  }
  async function onCalibrationMzCalibrateSampleProgress(data) {
    calibrationStatus.value = data
  }
  async function onCalibrationMzCalibrateSampleFinished(data) {
    calibrationStatus.value = data
    // Start matching in Scenthound automatically
    const instrumentStore = useInstrumentStore()
    if (instrumentStore.scenthoundModeActive) {
      instrumentStore.matchSimple(null)
    }
  }
  async function onCalibrationMzCalibrateSampleFailed(data) {
    calibrationStatus.value = { ...data, failed: true }
  }

  // mz_calibrate_batch
  async function onCalibrationMzCalibrateBatchStarted(data) {
    const notificationStore = useNotificationStore()
    notificationStore.onCalibrationStarted(data)
  }
  async function onCalibrationMzCalibrateBatchFinished(data) {
    const notificationStore = useNotificationStore()
    notificationStore.onCalibrationFinished(data)
  }
  // TODO_notifications  move to notification store, use the onActionFinished,
  // failed_calibration_samples is not used now from import_sample_items
  async function onCalibrationMzCalibrateBatchFailed(data) {
    const showWarningFailedCalibration = (payload) => {
      const notificationStore = useNotificationStore()
      notificationStore.showWarningNotification(payload)
      notificationStore.resetCalibrationNotification(null)
    }
    const failedCalibrationSamples = () => {
      const payload = {
        notification: 'failedCalibrationSamples',
        data: data.samples
      }
      const notificationStore = useNotificationStore()
      if (notificationStore.active) {
        setTimeout(() => {
          showWarningFailedCalibration(payload)
        }, 2000)
      } else {
        showWarningFailedCalibration(payload)
      }
    }

    const regularFail = () => {
      const notificationStore = useNotificationStore()
      notificationStore.onCalibrationFailed(data)
    }

    if (data.type === 'failed_calibration_samples') {
      failedCalibrationSamples()
    } else {
      regularFail()
    }
  }

  return {
    // state
    active,
    calibrationStatus,
    mzFit,
    mzFitError,
    mzFitStats,
    paramMatchScoreMin,
    paramMinIsotopeAbundance,
    paramMinPeakIntensity,
    paramRefineWindow,
    // getters
    params,
    // actions
    load,
    unload,
    getSampleMzCalibration,
    calibrationMzFit,
    calibrationMzApply,
    calibrationMzCalibrateSample,
    onCalibrationMzFitStarted,
    onCalibrationMzFitProgress,
    onCalibrationMzFitFinished,
    onCalibrationMzFitFailed,
    onCalibrationMzApplyStarted,
    onCalibrationMzApplyFinished,
    onCalibrationMzCalibrateSampleStarted,
    onCalibrationMzCalibrateSampleProgress,
    onCalibrationMzCalibrateSampleFinished,
    onCalibrationMzCalibrateSampleFailed,
    onCalibrationMzCalibrateBatchStarted,
    onCalibrationMzCalibrateBatchFinished,
    onCalibrationMzCalibrateBatchFailed
  }
})
