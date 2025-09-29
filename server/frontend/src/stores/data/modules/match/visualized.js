import { ref, computed, reactive, watch } from 'vue'
import { defineStore } from 'pinia'

import { api } from '@/api'
import { debounce, instrumentType as getInstrumentType } from '@/lib/utils'

import { useUi } from '@/stores/ui'

import { useWorkspace } from '../workspace'
import { useSample } from '../sample'
import { useMatchCollection, useMatchIon } from '../match'

import { useMatchParams } from './params'

// MATCH VISUALIZATION

export const useMatchVisualized = defineStore('app.data.match.visualized', () => {
  const ui = useUi()
  const matchParams = useMatchParams()
  const sample = useSample()
  const matchCollection = useMatchCollection()
  const matchIon = useMatchIon()

  // state
  const ion = ref(null)
  const isotopes = ref(null)
  const cache = reactive({
    sampleId: null,
    ionId: null,
    collectionId: null
  })

  const instrument = computed(() => sample.focused?.instrument)
  const instrumentType = computed(() => getInstrumentType(sample.focused?.instrument))

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
    const ionMatchParams = matchIon.list.find((ion) => ion.target_ion_id === ionId)?.filter_params[
      sample.focused.instrument
    ]

    // Reset filter parameters if the sample has changed and no new filter_parames to set are provided
    if (sampleChanged && !ionMatchParams) {
      matchParams.set()
    }

    // Load matches and activate visualization
    await load({ sampleId, ionId, collectionId, init: true })

    // Update cache to reflect the new state
    cache.sampleId = sampleId
    cache.ionId = ionId
    cache.collectionId = collectionId
  }

  async function reload({ init } = { init: false }) {
    await load({ init })
  }

  async function clear() {
    if (!ion.value) {
      return
    }
    ui.chart.clear()
    // reset values
    ion.value = null
    isotopes.value = null
    // clear cache
    cache.sampleId = null
    cache.ionId = null
    cache.collectionId = null
  }

  async function load({ sampleId, ionId, collectionId, init } = { init: true }) {
    // load matches
    const sample_item_id = sampleId ?? ion.value?.sample_item_id
    const target_ion_id = ionId ?? ion.value?.target_ion_id
    const target_collection_id = collectionId ?? ion.value?.target_collection_id
    if (!sample_item_id || !target_ion_id || !target_collection_id) {
      return
    }
    const sampleIon = await api.http.post(
      `/match/aggregate/sample/${sample_item_id}/ion`,
      {
        target_ion_id,
        target_collection_id,
        match_params: matchParams.ui
      },
      {
        use: 'read',
        type: 'load_matches'
      }
    )
    if (!sampleIon) {
      return
    }

    ion.value = sampleIon.match_ions[0]
    isotopes.value = sampleIon.match_isotopes.map(({ match_score, match_category, ...rest }) => ({
      ...rest,
      match: {
        match_score,
        match_category
      },
      color:
        isotopes.value?.find((existing) => existing.target_isotope_id === rest.target_isotope_id)
          ?.color ?? null, // Preserve color if exists
      mz: rest.mz.toFixed(4)
    }))

    if (init) {
      // use backend to init frontend params
      matchParams.set({ params: matchParams.db })
    }

    ui.chart.clear()

    await api.http.get(`/visualization/ion_focus`, {
      params: {
        sample_item_id: sampleId ?? ion.value.sample_item_id,
        target_ion_id: ionId ?? ion.value.target_ion_id,
        min_isotope_abundance: matchParams.ui.min_isotope_abundance,
        peak_min_intensity: matchParams.ui.peak_min_intensity,
        mz_tolerance: matchParams.ui.mz_tolerance
      },
      use: 'read',
      type: 'read_visualized_ion'
    })
  }

  // clear when switching workspaces
  const workspace = useWorkspace()
  watch(
    () => workspace.focused,
    () => {
      clear()
    }
  )

  // Watches for changes in the focused sample and updates the match visualization accordingly.
  watch(
    () => ({
      focusedSample: sample.focused,
      focusedIon: matchIon.focused,
      focusedCollection: matchCollection.focused
    }),
    async ({ focusedSample, focusedCollection, focusedIon }, old) => {
      const collectionChanged =
        focusedCollection?.target_collection_id !== old.focusedCollection?.target_collection_id
      // clear visualization if requirements are missing
      if (!focusedSample || !focusedIon || !focusedCollection || collectionChanged) {
        clear()
        return
      }

      // do nothing if no collection is focused
      let ionId = null
      let sampleId = focusedSample.sample_item_id
      let collectionId = focusedCollection.target_collection_id
      if (!collectionId) {
        return
      }

      if (ion.value) {
        // use visualized ion if set
        ionId = ion.value.target_ion_id
        collectionId = ion.value.target_collection_id
      } else if (focusedIon) {
        // no ion visualized but ion focused
        ionId = focusedIon.target_ion_id
      }
      // Set the focusedIon visualization with the new focusedSample ID, ion ID, collection ID, and filter params
      await set({
        sampleId,
        ionId,
        collectionId
      })
    }
  )

  return {
    // state
    ion,
    isotopes,
    instrument,
    instrumentType,
    // actions
    set: debounce(set),
    reload,
    clear
  }
})
