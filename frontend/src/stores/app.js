import { ref } from 'vue'
import { defineStore } from 'pinia'

import { api, extractDistinctValues } from '@/api'

export const useAppStore = defineStore('app', () => {
  const attributeTemplates = ref([])
  const instruments = ref([])
  const ionMechanisms = ref([])
  const pushNotification = ref(null)
  const mode = ref(import.meta.env.MASCOPE_PUBLIC_MODE)
  const ready = ref(false)
  const workspaces = ref([])

  // data loading
  async function load() {
    attributeTemplates.value = await getAllAttributeTemplates()
    instruments.value = await getAllInstrumentFunctions().then((funcs) =>
      extractDistinctValues(funcs, 'instrument')
    )
    ionMechanisms.value = await getAllIonizationMechanisms()
    workspaces.value = await getAllWorkspaces()

    ready.value = true

    api.log('loaded root data')
  }
  async function reload() {
    load()
  }
  // http client endpoints
  async function getAllAttributeTemplates() {
    const attributeTemplatesData = await api.request({
      httpMethod: 'getAllAttributeTemplates'
    })
    return attributeTemplatesData.data
  }
  async function getAllInstrumentFunctions() {
    const instrumentFunctions = await api.request({
      httpMethod: 'getAllInstrumentFunctions'
    })
    return instrumentFunctions.data
  }
  async function getAllIonizationMechanisms() {
    const ionizationMechanisms = await api.request({
      httpMethod: 'getAllIonizationMechanisms'
    })
    return ionizationMechanisms.data
  }
  async function getAllWorkspaces() {
    const workspaces = await api.request({
      httpMethod: 'getAllWorkspaces'
    })
    return workspaces.data
  }
  // backend notifications
  async function onOrgReload() {
    reload()
  }
  async function pushNotify(message) {
    pushNotification.value = message
  }

  return {
    attributeTemplates,
    instruments,
    ionMechanisms,
    mode,
    ready,
    workspaces,
    load,
    reload,
    getAllAttributeTemplates,
    getAllInstrumentFunctions,
    getAllIonizationMechanisms,
    getAllWorkspaces,
    onOrgReload,
    pushNotification,
    pushNotify
  }
})
