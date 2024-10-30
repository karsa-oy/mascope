import { ref, computed, watchEffect } from 'vue'
import { defineStore } from 'pinia'

import { api } from '@/api'

import { useMatchVisualized } from './visualized'


export const useMatchParams = defineStore('app.data.match.params', () => {
  const matchVisualized = useMatchVisualized()

  const defaults = ref()

  api.http.getParams().then((resp) => {
    defaults.value = resp?.data?.data?.params.match
  })

  const type = ref()
  const current = ref()
  const initial = ref()

  const areDefault = computed(() => {
    const typeDefaults = defaults.value[type.value];
    return Object.keys(typeDefaults)
      .every(
        (key) => current.value[key] === typeDefaults[key]
      )
  }
  )
  const changed = computed(() =>
    (initial.value && current.value)
      ? Object.keys(initial.value).some((key) => {
        return initial.value[key] !== current.value[key]
      })
      : null
  )

  function inferType(instrument) {
    if (!instrument) {
      return null
    }
    if (instrument.toLowerCase().includes('orbi')) {
      return 'orbi'
    } else if (instrument.toLowerCase().includes('tof') || instrument.toLowerCase().includes('api')) {
      return 'tof'
    }
  }

  async function set(opts) {
    type.value = opts?.type // priotize explicit type
      ?? inferType(opts?.instrument) // otherwise derive from instrument
      ?? type.value // fallback on prexisting value
    if (!type.value) {
      throw new Error('Match params: instrument type could not be infered')
    }
    current.value = {
      ...defaults.value[type.value],
      ...(opts?.params ?? {})
    }
  }
  async function reset({ instrument } = {}) {
    await set({
      instrument,
    })
  }

  async function save() {
    return await api.request.update({
      method: 'saveTargetIonMatchParams',
      body: {
        target_ion_id: matchVisualized.ion?.target_ion_id,
        target_ion_formula: matchVisualized.ion?.target_ion_formula,
        body: {
          match_params: {
            [matchVisualized.ion?.instrument]: current.value
          }
        }
      }
    })
  }
  async function remove() {
    return await api.request.delete({
      method: 'deleteTargetIonMatchParams',
      body: {
        target_ion_id: matchVisualized.ion.target_ion_id,
        target_ion_formula: matchVisualized.ion.target_ion_formula,
        body: {
          delete_instrument_filters: matchVisualized.ion.instrument
        }
      }
    })
  }

  async function init(opts) {
    await set(opts)
    initial.value = { ...current.value }
  }

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
