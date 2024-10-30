import { ref, computed, reactive, watch } from 'vue'
import { defineStore } from 'pinia'

import { api } from '@/api'
import { debounce } from '@/lib/utils'

import { useUi } from '@/stores/ui'

import { useWorkspace } from '../workspace'
import { useSample } from '../sample'

import { useMatchParams } from './params'
import { useMatchIon } from './records'

// MATCH VISUALIZATION

export const useMatchVisualized = defineStore('app.data.match.visualized', () => {
  const ui = useUi()
  const matchParams = useMatchParams()
  const sample = useSample()

  // state
  const ion = ref(null)
  const isotopes = ref(null)
  const cache = reactive({
    sampleId: null,
    ionId: null,
    collectionId: null
  })

  const instrument = computed(() => sample.focused.instrument)

  // actions
  /**
   * Sets the match visualization state based on the provided sample, ion, and collection IDs.
   *
   * - If a new sample is selected, filter parameters are reset to defaults.
   * - If any of the identifiers change (sample, ion, or collection), the corresponding matches are loaded, and the visualization is activated.
   * - If parameters are provided, they override the current filter parameters.
   *
   * @param {Object} options - The parameters for setting the match visualized.
   * @param {string|null} [options.sampleId] - The ID of the sample to visualize.
   * @param {string|null} [options.ionId] - The ID of the ion to visualize.
   * @param {string|null} [options.collectionId] - The ID of the collection to visualize.
   */
  async function set({
    sampleId = cache.sampleId,
    ionId = cache.ionId,
    collectionId = cache.collectionId
  }) {
    const sampleChanged = sampleId !== cache.sampleId
    const ionChanged = ionId !== cache.ionId
    const collectionChanged = collectionId !== cache.collectionId

    // Return early if nothing has changed
    if (!sampleChanged && !ionChanged && !collectionChanged) {
      return
    }

    // resolve ion filter params
    const matchIon = useMatchIon()
    const ionMatchParams = matchIon.list.find((ion) => ion.target_ion_id === ionId)?.filter_params[
      sample.focused.instrument
    ]

    // Reset filter parameters if the sample has changed and no new filter_parames to set are provided
    if (sampleChanged && !ionMatchParams) {
      await matchParams.reset({
        instrument: instrument.value
      })
    }

    // Apply new filter parameters if provided
    if (ionMatchParams) {
      await matchParams.init({
        params: ionMatchParams,
        instrument: instrument.value
      })
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

  async function unset({ cacheSample = false, cacheTarget = false } = {}) {
    if (!ion.value) {
      return
    }
    ui.chart.clear()
    if (!ion.value) return
    ion.value = null
    isotopes.value = null
    if (!cacheSample) {
      cache.sampleId = null
    }
    if (!cacheTarget) {
      cache.ionId = null
      cache.collectionId = null
    }
  }

  async function loadMatches({ sampleId, ionId, collectionId } = {}) {
    const target_ion_id = ionId ?? ion.value?.target_ion_id
    if (!target_ion_id) return
    const sampleIon = await api.http.post(
      `/match/aggregate/sample/${sampleId ?? ion.value?.sample_item_id}/ion`,
      {
        target_ion_id,
        target_collection_id: collectionId ?? ion.value?.target_collection_id,
        match_params: matchParams.current
      },
      {
        use: 'read',
        type: 'load_matches'
      }
    )
    if (!sampleIon) return
    const existingIsotopes = isotopes.value

    ion.value = sampleIon.match_ions[0]
    isotopes.value = sampleIon.match_isotopes.map((isotope) => {
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

    ui.chart.clear()

    await api.http.get(`/visualization/ion_focus`, {
      params: {
        sample_item_id: sampleId ?? ion.value.sample_item_id,
        target_ion_id: ionId ?? ion.value.target_ion_id,
        min_isotope_abundance: matchParams.current.min_isotope_abundance,
        peak_min_intensity: matchParams.current.peak_min_intensity,
        mz_tolerance: matchParams.current.mz_tolerance
      },
      use: 'read',
      type: 'read_visualized_ion'
    })
  }

  // clear when switching workspaces
  const workspace = useWorkspace()
  watch(
    computed(() => workspace.focused),
    () => {
      unset()
    }
  )

  return {
    // state
    ion,
    isotopes,
    // actions
    set: debounce(set),
    reset,
    unset
  }
})
