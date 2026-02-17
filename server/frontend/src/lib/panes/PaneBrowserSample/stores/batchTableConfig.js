import { ref, computed, watch } from 'vue'
import { defineStore } from 'pinia'

import { FilterMatchMode } from '@primevue/core/api'
import { useApp } from '@/stores'

export const useBatchTableConfig = defineStore('browser.sample.batchTable', () => {
  const app = useApp()

  // Store filtered batch list as reported by PrimeVue DataTable
  const filteredBatchList = ref([])

  const setFilteredBatchList = (list) => {
    filteredBatchList.value = list ?? []
  }

  const config = ref({
    sortField: 'sample_batch_name',
    sortOrder: -1,
    filters: {
      global: { value: null, matchMode: FilterMatchMode.CONTAINS }
    }
  })

  const defaultConfig = {
    sortField: 'sample_batch_name',
    sortOrder: -1,
    filters: {
      global: { value: null, matchMode: FilterMatchMode.CONTAINS }
    }
  }

  const isDefault = computed(() => JSON.stringify(config.value) === JSON.stringify(defaultConfig))
  const isInitialized = computed(() => JSON.stringify(config.value) !== '{}')

  // local storage persistence

  const storageKey = computed(() => `sample-browser-workspace[${app.data.workspace.focusedId}]`)

  // write to local storage
  function writeConfig() {
    if (isInitialized.value && !isDefault.value) {
      const newState = JSON.stringify(config.value)
      localStorage.setItem(storageKey.value, newState)
    }
  }

  // read from local storage, falling back on default
  function readConfig() {
    const storedState = localStorage.getItem(storageKey.value)
    const defaultState = JSON.stringify(defaultConfig)
    config.value = JSON.parse(storedState ?? defaultState)
  }

  // reset to default config and clear local storage
  function resetConfig() {
    config.value = { ...defaultConfig }
    localStorage.removeItem(storageKey.value)
  }

  // write to local storage when any options update
  watch(() => config.value, writeConfig, { deep: true })

  // read from local storage when workspace changes
  watch(
    () => app.data.workspace.focusedId,
    () => {
      if (app.data.workspace.focusedId) {
        readConfig()
      }
    },
    { immediate: true }
  )

  // Initialize filteredBatchList when batch list changes (for when no filter is active)
  watch(
    () => app.data.batch.list,
    (newList) => {
      if (!config.value.filters?.global?.value) {
        filteredBatchList.value = newList ?? []
      }
    },
    { immediate: true }
  )

  return {
    config,
    filteredBatchList,
    setFilteredBatchList,
    resetConfig
  }
})
