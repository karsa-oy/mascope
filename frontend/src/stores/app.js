import { ref, reactive } from 'vue'
import { defineStore } from 'pinia'

import { api, extractDistinctValues } from '@/api'
import { useInstrumentStore } from './instrument'

export const useAppStore = defineStore('app', () => {
  const instrumentStore = useInstrumentStore()

  const attributeTemplates = ref([])
  const instruments = ref([])
  const ionMechanisms = ref([])
  const mode = reactive({
    measuring: false,
    dark: true
  })
  const savedSplit = JSON.parse(localStorage.getItem('mascope-dashboard-split'))
  const split = reactive({
    left: savedSplit[0],
    right: savedSplit[1]
  })
  const ready = ref(false)
  const workspaces = ref([])

  // data loading
  async function load() {
    // init darkmode
    const systemPreference = window.matchMedia('(prefers-color-scheme:dark)').matches
    const savedPreference =
      localStorage.getItem('mascope-darkmode') == 'true'
        ? true
        : localStorage.getItem('mascope-darkmode') == 'false'
          ? false
          : null
    mode.dark = savedPreference ?? systemPreference ?? true
    if (mode.dark) {
      document.body.classList.add('darkmode')
    }
    // init data
    attributeTemplates.value = (
      await api.request.read({
        method: 'getAllAttributeTemplates'
      })
    )?.data
    instruments.value = await api.request
      .read({
        method: 'getAllInstrumentFunctions'
      })
      .then((res) => extractDistinctValues(res.data, 'instrument'))
    instrumentStore.active = instruments.value[0]
    ionMechanisms.value = (
      await api.request.read({
        method: 'getAllIonizationMechanisms'
      })
    )?.data
    workspaces.value = (
      await api.request.read({
        method: 'getAllWorkspaces'
      })
    )?.data

    ready.value = true

    api.log('loaded root data')
  }
  async function onOrgReload() {
    load()
  }

  return {
    attributeTemplates,
    instruments,
    ionMechanisms,
    mode,
    ready,
    workspaces,
    split,
    load,
    onOrgReload
  }
})
