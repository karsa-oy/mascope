import { ref, computed, reactive, watch } from 'vue'
import { defineStore } from 'pinia'

import { api } from '@/api'
import { debounce, instrumentType as getInstrumentType } from '@/lib/utils'

import { useUi } from '@/stores/ui'

import { useWorkspace } from '../workspace'
import { useSample } from '../sample'

import { useMatchParams } from './params'
import { useMatchIon, useMatchCompound, useMatchCollection } from './records'

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
    const matchIon = useMatchIon()
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
    const target_ion_id = ionId ?? ion.value?.target_ion_id
    if (!target_ion_id) return
    const sampleIon = await api.http.post(
      `/match/aggregate/sample/${sampleId ?? ion.value?.sample_item_id}/ion`,
      {
        target_ion_id,
        target_collection_id: collectionId ?? ion.value?.target_collection_id,
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
    isotopes.value = sampleIon.match_isotopes.map((isotope) => ({
      ...isotope,
      color:
        isotopes.value?.find((existing) => existing.target_isotope_id === isotope.target_isotope_id)
          ?.color ?? null, // Preserve color if exists
      mz: isotope.mz.toFixed(4)
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

  /**
   * Watches for changes in the focused sample and updates the match visualization accordingly.
   *
   * This watcher reacts whenever `app.data.sample.focused` changes:
   * - Scenario 1: Match Tab is active (app.data.match.visualized.ion is set)
   *   - If a new sample is focused and there's an ion currently visualized in the Match tab,
   *     the function retrieves the corresponding data from `app.data.match.visualized.ion`.
   *   - The match visualization is then updated with the new sample ID,  visualised ion ID, collection ID, and its filter parameters.
   *
   * - Scenario 2: Target selection in Target Browser (app.data.match.visualized.ion is inactive):
   *   - If no ion is currently visualized but there is a selected ion in the Target browser,
   *     it retrieves the focused ion and the appropriate filter parameters from `app.data.match.ion.selected`.
   *   - If a compound is selected instead, it finds the corresponding ion from the loaded ions and retrieves its filter parameters.
   *   - The match visualization is then triggered with the selected sample, ion, and selected collection details.
   *
   * - Unsetting the Match Visualization:
   *   - If no sample is focused, the match visualization tab is cleared by calling `unset`.
   *
   * @param {Object|null} newFocusedSample - The new sample that has been focused, or null if no sample is focused.
   */
  watch(
    () => sample.focused,
    async (sample) => {
      // clear visualization if no sample focused
      if (!sample) {
        clear()
        return
      }
      const matchCollection = useMatchCollection()

      // do nothing if no collection is focused
      let collectionId = matchCollection.focusedId
      if (!collectionId) {
        return
      }

      const matchIon = useMatchIon()
      const matchCompound = useMatchCompound()
      let sampleId = sample.sample_item_id
      let ionId = null

      if (ion.value) {
        // use match visualized
        ionId = ion.value.target_ion_id
        collectionId = ion.value.target_collection_id
      } else if (matchIon.focused) {
        // no match visualized but match ion focused
        ionId = matchIon.focused.target_ion_id
      } else if (matchCompound.focused) {
        // no match visualized but match compound focused
        ionId = matchIon.list?.find(
          (ion) => ion.target_compound_id === matchCompound.focusedId
        )?.target_ion_id
      }

      if (ionId && collectionId) {
        // Set the match visualization with the new sample ID, ion ID, collection ID, and filter params
        await set({
          sampleId,
          ionId,
          collectionId
        })
      }
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
