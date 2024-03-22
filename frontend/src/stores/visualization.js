import { ref, computed } from 'vue'
import { defineStore } from 'pinia'

import { handleApiRequest, getApiData, snakeToCamel } from './lib/api'
import { useTargetsStore } from './targets'

export const useVisualizationStore = defineStore('visualization', () => {
  // state

  const activeIon = ref(null)
  const activeIsotopes = ref(null)
  // filter parameters
  const paramMzTolerance = ref(0)
  const paramMinIsotopeAbundance = ref(0)
  const paramIsotopeRatioTolerance = ref(0)
  const paramPeakMinIntensity = ref(0)
  const paramMinIsotopeCorrelation = ref(0)
  const paramProbableMatchThreshold = ref(0)
  const paramPossibleMatchThreshold = ref(0)
  // chart data
  const tracesSignalTimeseries = ref(null)
  const tracesSignalSumSpectrum = ref(null)

  // TODO_configuration Default filter parameters
  const paramDefaults = {
    mz_tolerance: 15,
    min_isotope_abundance: 0.15,
    isotope_ratio_tolerance: 0.15,
    peak_min_intensity: 0,
    min_isotope_correlation: 0.8,
    probable_match_threshold: 0.8,
    possible_match_threshold: 0.7
  }

  // getters
  const getActiveIsotopes = computed(() => {
    return activeIsotopes.value ?? []
  })
  const defaultFilterParams = computed(() => {
    // Transform paramDefaults keys to camelCase and prepend 'param'
    const transformedParamDefaults = Object.entries(paramDefaults).reduce((acc, [key, value]) => {
      // Prepend 'param' and convert to camelCase
      const camelCaseKey = 'param' + snakeToCamel(key.charAt(0).toUpperCase() + key.slice(1))
      acc[camelCaseKey] = value
      return acc
    }, {})
    return transformedParamDefaults
  })

  // actions

  // data loading
  async function load({ sampleId, ionId, collectionId, filterParams = null }) {
    await unload()
    await setFilterParams(filterParams ?? paramDefaults)

    await loadMatches({ sampleId, ionId, collectionId })
    await loadVisualizationIonFocus({ sampleId, ionId })
  }

  async function loadMatches(params = {}) {
    const sampleId = params?.sampleId ?? activeIon.value.sample_item_id
    const ionId = params?.ionId ?? activeIon.value.target_ion_id
    const collectionId = params?.collectionId ?? activeIon.value.target_collection_id

    const sampleIonData = await getSampleIonData({
      sampleId,
      ionId,
      collectionId
    })

    const existingIsotopes = activeIsotopes.value

    activeIsotopes.value = sampleIonData.match_isotopes.map((isotope) => {
      let existingIsotope = null
      if (existingIsotopes) {
        existingIsotope = existingIsotopes.find(
          (existing) => existing.target_isotope_id === isotope.target_isotope_id
        )
      }

      return {
        target_isotope_id: isotope.target_isotope_id,
        color: existingIsotope?.color || null, // Preserve color if exists
        mz: isotope.mz.toFixed(4),
        match_score: isotope.match_score,
        match_category: isotope.match_category,
        alarm_mode: isotope.alarm_mode,
        target_collection_type: isotope.target_collection_type,
        relative_abundance: isotope.relative_abundance,
        sample_peak_area: isotope.sample_peak_area,
        match_mz_error: isotope.match_mz_error,
        match_abundance_error: isotope.match_abundance_error,
        match_isotope_correlation: isotope.match_isotope_correlation
      }
    })
    activeIon.value = sampleIonData.match_ions[0]
  }

  async function loadVisualizationIonFocus(params = {}) {
    const sampleId = params?.sampleId ?? activeIon.value.sample_item_id
    const ionId = params?.ionId ?? activeIon.value.target_ion_id

    if (tracesSignalTimeseries.value && tracesSignalSumSpectrum.value) await resetVisualization()

    await getVisualizationIonFocus({
      sampleId,
      ionId
    })
  }

  async function reload() {
    await loadMatches()
    await loadVisualizationIonFocus()
  }

  async function resetVisualization() {
    if (!tracesSignalTimeseries.value && !tracesSignalSumSpectrum.value) return
    tracesSignalSumSpectrum.value = null
    tracesSignalTimeseries.value = null
  }

  async function unload() {
    // visualisation
    resetVisualization()
    if (!activeIon.value) return
    activeIon.value = null
    activeIsotopes.value = null
  }

  // parameters
  async function setFilterParams(params = null) {
    // Use provided params, then check if there is ion-specific filter params for that ion and sampleItem instrument
    const filterParams =
      params ?? activeIon.value?.filter_params?.[activeIon.value.instrument] ?? {}

    // Use instrument-specific filter params or fallback to defaults
    paramMzTolerance.value = filterParams.mz_tolerance ?? paramDefaults.mz_tolerance
    paramMinIsotopeAbundance.value =
      filterParams.min_isotope_abundance ?? paramDefaults.min_isotope_abundance
    paramIsotopeRatioTolerance.value =
      filterParams.isotope_ratio_tolerance ?? paramDefaults.isotope_ratio_tolerance
    paramPeakMinIntensity.value =
      filterParams.peak_min_intensity ?? paramDefaults.peak_min_intensity
    paramMinIsotopeCorrelation.value =
      filterParams.min_isotope_correlation ?? paramDefaults.min_isotope_correlation
    paramProbableMatchThreshold.value =
      filterParams.probable_match_threshold ?? paramDefaults.probable_match_threshold
    paramPossibleMatchThreshold.value =
      filterParams.possible_match_threshold ?? paramDefaults.possible_match_threshold
  }
  async function setDefaultFilterParams() {
    await setFilterParams(paramDefaults)
  }

  // http client endpoints
  async function getSampleIonData({ sampleId, ionId, collectionId }) {
    const targetsStore = useTargetsStore()
    const alarmsList = targetsStore.alarmsList

    const body = {
      target_ion_id: ionId,
      target_collection_id: collectionId,
      filter_params: {
        mz_tolerance: paramMzTolerance.value,
        isotope_ratio_tolerance: paramIsotopeRatioTolerance.value,
        peak_min_intensity: paramPeakMinIntensity.value,
        min_isotope_abundance: paramMinIsotopeAbundance.value,
        min_isotope_correlation: paramMinIsotopeCorrelation.value,
        probable_match_threshold: paramProbableMatchThreshold.value,
        possible_match_threshold: paramPossibleMatchThreshold.value
      },
      alarms_list: alarmsList
    }

    const sampleIonData = await getApiData({
      httpMethod: 'getSampleIonMatches',
      requestData: {
        sampleId,
        body
      },
      errorMessage: `Failed to load sample ion data.`
    })
    return sampleIonData.data
  }

  async function getVisualizationIonFocus({ sampleId, ionId }) {
    return await getApiData({
      httpMethod: 'getVisualizationIonFocus',
      requestData: {
        sample_item_id: sampleId,
        target_ion_id: ionId,
        min_isotope_abundance: paramMinIsotopeAbundance.value,
        peak_min_intensity: paramPeakMinIntensity.value,
        mz_tolerance: paramMzTolerance.value
      }
    })
  }

  async function submitMatchRating(newMatchRating) {
    return await handleApiRequest({
      httpMethod: 'submitMatchRating',
      requestData: newMatchRating,
      successMessage: 'Rating submitted successfully. Thanks for your feedback!',
      errorMessage: 'Failed to submit rating. Please try again.'
    })
  }
  async function saveFilterParams() {
    const targetIonUpdate = {
      target_ion_id: activeIon.value.target_ion_id,
      target_ion_formula: activeIon.value.target_ion_formula,
      body: {
        filter_params: {
          [activeIon.value.instrument]: {
            mz_tolerance: paramMzTolerance.value,
            isotope_ratio_tolerance: paramIsotopeRatioTolerance.value,
            peak_min_intensity: paramPeakMinIntensity.value,
            min_isotope_abundance: paramMinIsotopeAbundance.value,
            min_isotope_correlation: paramMinIsotopeCorrelation.value,
            probable_match_threshold: paramProbableMatchThreshold.value,
            possible_match_threshold: paramPossibleMatchThreshold.value
          }
        }
      }
    }
    return await handleApiRequest({
      httpMethod: 'updateTargetIon',
      requestData: targetIonUpdate,
      successMessage: `Filtering parameters for ${targetIonUpdate.target_ion_formula} saved successfully!`,
      errorMessage: 'Failed to save filtering parameters. Please try again.'
    })
  }
  async function deleteInstrumentFilterParams() {
    const targetIonUpdate = {
      target_ion_id: activeIon.value.target_ion_id,
      target_ion_formula: activeIon.value.target_ion_formula,
      body: {
        delete_instrument_filters: activeIon.value.instrument
      }
    }
    return await handleApiRequest({
      httpMethod: 'updateTargetIon',
      requestData: targetIonUpdate,
      successMessage: `Filtering parameters for ${targetIonUpdate.body.delete_instrument_filters} instrument were deleted successfully!`,
      errorMessage: 'Failed to delete filtering parameters. Please try again.'
    })
  }

  // backend notifications
  async function onVisualizationSignalSumSpectrum(traces) {
    for (let trace of traces) {
      trace.x = new Float32Array(trace.x)
      trace.y = new Float32Array(trace.y)

      // Check if the trace has target_isotope_id and update the corresponding isotope in activeIsotopes
      if (trace.target_isotope_id) {
        const isotope = activeIsotopes.value.find(
          (iso) => iso.target_isotope_id === trace.target_isotope_id
        )
        if (isotope) {
          // Extract RGB values and convert them to the 0-255 range
          const colorParts = trace.line.color.match(/(\d+\.?\d*)/g)
          if (colorParts) {
            const r = Math.round(parseFloat(colorParts[0]) * 255)
            const g = Math.round(parseFloat(colorParts[1]) * 255)
            const b = Math.round(parseFloat(colorParts[2]) * 255)
            isotope.color = `rgb(${r},${g},${b})`
          }
        }
      }
    }
    const existingTraces = tracesSignalSumSpectrum.value
    if (existingTraces) traces = [...existingTraces, ...traces]
    tracesSignalSumSpectrum.value = traces
  }
  async function onVisualizationSignalTimeseries(traces) {
    for (let trace of traces) {
      trace.x = new Float32Array(trace.x)
      trace.y = new Float32Array(trace.y)
    }
    const existingTraces = tracesSignalTimeseries.value
    if (existingTraces) traces = [...existingTraces, ...traces]
    tracesSignalTimeseries.value = traces
  }

  return {
    // state
    activeIon,
    activeIsotopes,
    paramMzTolerance,
    paramMinIsotopeAbundance,
    paramPeakMinIntensity,
    paramMinIsotopeCorrelation,
    paramProbableMatchThreshold,
    paramPossibleMatchThreshold,
    tracesSignalTimeseries,
    tracesSignalSumSpectrum,
    // getters
    getActiveIsotopes,
    defaultFilterParams,
    // actions
    load,
    loadMatches,
    loadVisualizationIonFocus,
    reload,
    unload,
    setFilterParams,
    setDefaultFilterParams,
    getSampleIonData,
    getVisualizationIonFocus,
    submitMatchRating,
    saveFilterParams,
    deleteInstrumentFilterParams,
    onVisualizationSignalSumSpectrum,
    onVisualizationSignalTimeseries
  }
})
