import { ref, computed } from 'vue'
import { defineStore } from 'pinia'

import { api } from '@/api'
import { instrumentType } from '@/lib/utils'
import { useAuth } from '@/stores/auth'

import { useMatchVisualized } from './visualized'

export const useMatchParams = defineStore('app.data.match.params', () => {
  const matchVisualized = useMatchVisualized()

  const defaults = ref()

  const auth = useAuth()

  auth.onLogin(() => {
    api.http
      .get('/params', {
        type: 'read_params'
      })
      .then(({ data }) => {
        defaults.value = data?.data?.params.match
      })
  })

  const type = ref()
  const current = ref()
  const initial = ref()

  const areDefault = computed(() => {
    if (type.value) {
      const typeDefaults = defaults.value[type.value]
      return Object.keys(typeDefaults).every((key) => current.value[key] === typeDefaults[key])
    } else {
      return
    }
  })
  const changed = computed(() =>
    initial.value && current.value
      ? Object.keys(initial.value).some((key) => {
          return initial.value[key] !== current.value[key]
        })
      : null
  )

  async function set(opts) {
    type.value =
      opts?.type ?? // priotize explicit type
      instrumentType(opts?.instrument) ?? // otherwise derive from instrument
      type.value // fallback on prexisting value
    if (!type.value) {
      throw new Error('Match params: failed to resolve instrument type')
    }
    current.value = {
      ...defaults.value[type.value],
      ...(opts?.params ?? {})
    }
  }
  async function reset({ instrument } = {}) {
    await set({
      instrument
    })
  }

  async function save() {
    return await api.http.patch(
      `/target/ions/${matchVisualized.ion?.target_ion_id}`,
      {
        match_params: {
          [matchVisualized.ion?.instrument]: current.value
        }
      },
      {
        use: 'update',
        type: 'save_ion_match_params'
      }
    )
  }
  async function remove() {
    return await api.http.patch(
      `/target/ions/${matchVisualized.ion.target_ion_id}`,
      {
        delete_instrument_filters: matchVisualized.ion.instrument
      },
      {
        use: 'delete',
        type: 'remove_ion_match_params'
      }
    )
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
