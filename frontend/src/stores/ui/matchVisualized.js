import { ref, computed, reactive, watch } from 'vue'
import { defineStore } from 'pinia'

import { api } from '@/api'
import { debounce } from '@/lib/utils'

import { useData } from '../data'
import { useChart } from './chart'

// MATCH VISUALIZATION

export const useMatchVisualized = defineStore('app.ui.matchVisualized', () => {
  const data = useData()

  // state
  const ion = ref(null)
  const isotopes = ref(null)
  const cache = reactive({
    sampleId: null,
    ionId: null,
    collectionId: null
  })

  const hash = computed(() => {
    const sampleId = ion.value?.sample_item_id
    const collectionId = ion.value?.target_collection_id
    const ionId = ion.value?.target_ion_id
    return sampleId && collectionId && ionId ? `${sampleId}_${collectionId}_${ionId}` : null
  })

  const filterParams = computed(() =>
    hash.value ? ion.value?.filter_params[data.sample.focused.instrument] : null
  )

  // actions
  /**
   * Sets the match visualization state based on the provided sample, ion, and collection IDs.
   *
   * - If a new sample is selected, filter parameters are reset to defaults.
   * - If any of the identifiers change (sample, ion, or collection), the corresponding matches are loaded, and the visualization is activated.
   * - If parameters are provided, they override the current filter parameters.
   *
   * @param {Object} options - The parameters for setting the matchVisualized.
   * @param {string|null} [options.sampleId] - The ID of the sample to visualize.
   * @param {string|null} [options.ionId] - The ID of the ion to visualize.
   * @param {string|null} [options.collectionId] - The ID of the collection to visualize.
   * @param {Object|null} [options.params] - Optional filter parameters to apply.
   */
  async function set({
    sampleId = cache.sampleId,
    ionId = cache.ionId,
    collectionId = cache.collectionId,
    params = null
  }) {
    const sampleChanged = sampleId !== cache.sampleId
    const ionChanged = ionId !== cache.ionId
    const collectionChanged = collectionId !== cache.collectionId

    // Return early if nothing has changed
    if (!sampleChanged && !ionChanged && !collectionChanged) {
      return
    }
    // Reset filter parameters if the sample has changed and no new filter_parames to set are provided
    if (sampleChanged && !params) {
      await data.filterParams.reset()
    }

    // Apply new filter parameters if provided
    if (params) {
      await data.filterParams.set(params)
    }

    // Load matches and activate visualization
    await loadMatches({ sampleId, ionId, collectionId })
    await activate({ sampleId, ionId })

    // Update cache to reflect the new state
    cache.sampleId = sampleId
    cache.ionId = ionId
    cache.collectionId = collectionId
  }

  async function reset() {
    await loadMatches()
    await activate()
  }

  async function unset({ sample = true, target = true } = {}) {
    const chart = useChart()
    chart.clear()
    if (!ion.value) return
    ion.value = null
    isotopes.value = null
    if (sample) {
      cache.sampleId = null
    }
    if (target) {
      cache.ionId = null
      cache.collectionId = null
    }
  }

  async function loadMatches({ sampleId, ionId, collectionId } = {}) {
    const target_ion_id = ionId ?? ion.value?.target_ion_id
    if (!target_ion_id) return
    const sampleIon = await api.request.read({
      method: 'getAggregateSampleMatchIon',
      body: {
        sampleId: sampleId ?? ion.value?.sample_item_id,
        body: {
          target_ion_id,
          target_collection_id: collectionId ?? ion.value?.target_collection_id,
          filter_params: data.filterParams.current
        }
      }
    })
    if (!sampleIon?.data) return
    const existingIsotopes = isotopes.value

    ion.value = sampleIon.data.match_ions[0]
    isotopes.value = sampleIon.data.match_isotopes.map((isotope) => {
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
  }

  async function activate({ sampleId, ionId } = {}) {
    if (!ion.value) return
    const chart = useChart()

    chart.clear()

    await api.request.read({
      method: 'getVisualizationIonFocus',
      body: {
        sample_item_id: sampleId ?? ion.value.sample_item_id,
        target_ion_id: ionId ?? ion.value.target_ion_id,
        min_isotope_abundance: data.filterParams.current.min_isotope_abundance,
        peak_min_intensity: data.filterParams.current.peak_min_intensity,
        mz_tolerance: data.filterParams.current.mz_tolerance
      }
    })
  }

  watch(
    computed(() => data.workspace.focused),
    () => {
      unset()
    }
  )

  return {
    // state
    ion,
    isotopes,
    hash,
    filterParams,
    // actions
    set: debounce(set),
    reset,
    unset
  }
})
