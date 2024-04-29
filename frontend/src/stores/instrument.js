import { ref } from 'vue'
import { defineStore } from 'pinia'

import { api } from '@/api'

import { useCalibrationStore } from './calibration'
import { useSampleStore } from './sample'

export const useInstrumentStore = defineStore('instrument', () => {
  const active = ref(null)
  const acquisitionActiveFilename = ref(null)
  const acquisitionProgress = ref(0)
  const acquisitions = ref(null)
  const conversionProgress = ref(0)
  const matchingProgress = ref(0)
  const mzCalibration = ref(null)
  const recentAcquisitions = ref(null)
  const sampleItemPending = ref(null)
  const scenthoundModeActive = ref(false)

  // data loading
  async function load(instrument) {
    if (active.value) await unload()
    api.emit('subscribe', instrument)
    active.value = instrument
    await loadMzCalibration()
    await loadRecentAcquisitions()
  }

  async function loadMzCalibration() {
    const lastMzCalibration = await getLastMzCalibration()
    if (!lastMzCalibration) return
    mzCalibration.value = lastMzCalibration
  }

  async function loadAcquisitions(datetimeRange) {
    const sampleFiles = await getSampleFiles(datetimeRange)
    if (!sampleFiles) return
    acquisitions.value = sampleFiles
  }

  async function loadRecentAcquisitions() {
    const recentAcquisitionsData = await getRecentSampleFiles()
    if (!recentAcquisitionsData) return
    recentAcquisitions.value = recentAcquisitionsData
  }

  async function resetAcquisitionStatus() {
    acquisitionActiveFilename.value = null
    acquisitionProgress.value = 0
    const calibrationStore = useCalibrationStore()
    calibrationStore.calibrationStatus = null
    conversionProgress.value = 0
    matchingProgress.value = 0
  }

  async function unload() {
    if (!active.value) return
    api.emit('unsubscribe', active.value)
    active.value = null
    mzCalibration.value = null
    acquisitions.value = null
    recentAcquisitions.value = null
    await resetAcquisitionStatus()
    scenthoundModeActive.value = false
  }

  async function matchSample() {
    const sampleStore = useSampleStore()
    const calibrationVerified = sampleStore.active?.mz_calibration.verified
    if (calibrationVerified) {
      await sampleStore.matchSampleCompute(sampleStore.active)
    } else {
      // Try again in 1 second if scenthound is still opened
      if (!scenthoundModeActive.value) return
      setTimeout(() => {
        matchSample()
      }, 1000)
    }
  }

  // http client endpoints
  async function getSampleFiles(datetimeRange) {
    const reqData = {
      datetime_min: datetimeRange.min.toISOString(),
      datetime_max: datetimeRange.max.toISOString(),
      instrument: active.value,
      sort: 'datetime_utc',
      order: 'asc'
    }

    const sampleFiles = await api.request({
      httpMethod: 'getAllSampleFiles',
      requestData: reqData
    })
    return sampleFiles?.data ?? null
  }

  async function getRecentSampleFiles() {
    const reqData = {
      instrument: active.value,
      sort: 'datetime_utc',
      order: 'asc'
    }

    const sampleFiles = await api.request({
      httpMethod: 'getRecentSampleFiles',
      requestData: reqData
    })
    return sampleFiles?.data ?? null
  }

  async function getLastMzCalibration() {
    const reqData = {
      instrument: active.value
    }

    const mzCalibration = await api.request({
      httpMethod: 'getMzCalibration',
      requestData: reqData
    })

    return mzCalibration
  }

  // backend notifications
  async function onInstrumentAcquisitionFinished({ filename, progress }) {
    acquisitionActiveFilename.value = filename
    acquisitionProgress.value = progress
  }
  async function onInstrumentAcquisitionProgress({ filename, progress }) {
    acquisitionActiveFilename.value = filename
    acquisitionProgress.value = progress
  }
  async function onInstrumentAcquisitionStarted({ filename, progress }) {
    const sampleStore = useSampleStore()
    await sampleStore.unload()
    await resetAcquisitionStatus()
    acquisitionActiveFilename.value = filename
    acquisitionProgress.value = progress
  }
  async function onInstrumentConversionFinished({ progress }) {
    conversionProgress.value = progress
    // Wait for sample to be saved, then start mass calibration
    if (scenthoundModeActive.value) {
      const calibrationStore = useCalibrationStore()
      calibrationStore.calibrationMzCalibrateSample()
    }
  }
  async function onInstrumentConversionProgress({ progress }) {
    conversionProgress.value = progress
  }
  async function onInstrumentConversionStarted({ progress }) {
    conversionProgress.value = progress
  }
  async function onMatchItemComputeStarted({ progress }) {
    matchingProgress.value = progress
  }
  async function onMatchItemComputeProgress({ progress }) {
    matchingProgress.value = progress
  }
  async function onMatchItemComputeFinished({ progress }) {
    matchingProgress.value = progress
    // TODO: case: background, verify interferences
    // TODO: case: else, display matches
  }
  async function onMatchItemComputeFailed({ progress }) {
    matchingProgress.value = progress
  }
  async function onSampleFileCreated() {
    console.log('onSampleFileCreated')
    await loadRecentAcquisitions()
    if (scenthoundModeActive.value) {
      console.log('scenthound active')
      if (sampleItemPending.value) {
        console.log('sample item pending')
        const sampleStore = useSampleStore()
        await sampleStore.create(sampleItemPending.value)
        sampleItemPending.value = null
      }
    }
  }

  return {
    // state
    active,
    acquisitionActiveFilename,
    acquisitionProgress,
    acquisitions,
    conversionProgress,
    matchingProgress,
    mzCalibration,
    recentAcquisitions,
    sampleItemPending,
    scenthoundModeActive,
    // actions
    load,
    loadMzCalibration,
    loadAcquisitions,
    loadRecentAcquisitions,
    resetAcquisitionStatus,
    unload,
    matchSample,
    getSampleFiles,
    getRecentSampleFiles,
    getLastMzCalibration,
    onInstrumentAcquisitionFinished,
    onInstrumentAcquisitionProgress,
    onInstrumentAcquisitionStarted,
    onInstrumentConversionFinished,
    onInstrumentConversionProgress,
    onInstrumentConversionStarted,
    onMatchItemComputeFailed,
    onMatchItemComputeFinished,
    onMatchItemComputeProgress,
    onMatchItemComputeStarted,
    onSampleFileCreated
  }
})
