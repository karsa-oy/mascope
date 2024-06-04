import { ref, reactive, computed, watchEffect } from 'vue'
import { defineStore } from 'pinia'

import { api } from '@/api'

import { useFocusedMatch } from './focusedMatch'

export const useFilterParams = defineStore('filterParams', () => {
  const defaults = {
    mz_tolerance: 15,
    min_isotope_abundance: 0.15,
    isotope_ratio_tolerance: 0.15,
    peak_min_intensity: 0,
    min_isotope_correlation: 0.8,
    probable_match_threshold: 0.8,
    possible_match_threshold: 0.7
  }
  const current = reactive({ ...defaults })
  const initial = ref({ ...defaults })
  const hash = ref()

  const areDefault = computed(() =>
    Object.keys(defaults).every((key) => current[key] === defaults[key])
  )
  const changed = computed(() =>
    Object.keys(initial.value).some((key) => {
      return initial.value[key] !== current[key]
    })
  )

  async function set(params = {}) {
    // fallback to defaults for missing params
    current.mz_tolerance = params?.mz_tolerance ?? defaults.mz_tolerance
    current.min_isotope_abundance = params?.min_isotope_abundance ?? defaults.min_isotope_abundance
    current.isotope_ratio_tolerance =
      params?.isotope_ratio_tolerance ?? defaults.isotope_ratio_tolerance
    current.peak_min_intensity = params?.peak_min_intensity ?? defaults.peak_min_intensity
    current.min_isotope_correlation =
      params?.min_isotope_correlation ?? defaults.min_isotope_correlation
    current.probable_match_threshold =
      params?.probable_match_threshold ?? defaults.probable_match_threshold
    current.possible_match_threshold =
      params?.possible_match_threshold ?? defaults.possible_match_threshold
  }
  async function reset() {
    await set(defaults)
  }

  async function save() {
    const match = useFocusedMatch()
    return await api.request.update({
      method: 'saveTargetIonFilterParams',
      body: {
        target_ion_id: match.ion?.target_ion_id,
        target_ion_formula: match.ion?.target_ion_formula,
        body: {
          filter_params: {
            [match.ion?.instrument]: current
          }
        }
      }
    })
  }
  async function remove() {
    const focusedMatch = useFocusedMatch()
    return await api.request.delete({
      method: 'deleteTargetIonFilterParams',
      body: {
        target_ion_id: focusedMatch.ion.target_ion_id,
        target_ion_formula: focusedMatch.ion.target_ion_formula,
        body: {
          delete_instrument_filters: focusedMatch.ion.instrument
        }
      }
    })
  }

  function init() {
    initial.value = { ...current }
  }

  const focusedMatch = useFocusedMatch()
  watchEffect(async () => {
    if (focusedMatch.hash) {
      if (focusedMatch.hash !== hash.value) {
        await set(focusedMatch.filterParams)
        init()
        hash.value = focusedMatch.hash
      }
    } else {
      hash.value = null
    }
  })

  return {
    current,
    initial,
    default: areDefault,
    changed,
    set,
    init,
    reset,
    save,
    remove
  }
})
