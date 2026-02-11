import { ref, computed, watch } from 'vue'
import { defineStore } from 'pinia'

import { FilterMatchMode } from '@primevue/core/api'
import { useApp } from '@/stores'

export const useBatchTableConfig = defineStore('browser.sample.batchTable', () => {
  const app = useApp()

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

  // sorted batch list
  const sortedBatchList = computed(() => {
    if (!app.data.batch.list || app.data.batch.list.length === 0) return []

    const list = [...app.data.batch.list]
    const { sortField, sortOrder } = config.value

    if (!sortField) return list

    return list.sort((a, b) => {
      const aVal = a[sortField]
      const bVal = b[sortField]

      if (aVal == null && bVal == null) return 0
      if (aVal == null) return 1
      if (bVal == null) return -1

      if (typeof aVal === 'string' && typeof bVal === 'string') {
        return sortOrder * aVal.localeCompare(bVal)
      }

      return sortOrder * (aVal < bVal ? -1 : aVal > bVal ? 1 : 0)
    })
  })

  // sorted and filtered batch list
  const sortedFilteredBatchList = computed(() => {
    let list = sortedBatchList.value

    const globalFilter = config.value.filters?.global?.value
    if (!globalFilter) return list

    // Apply global filter - check if any field contains the filter value (case-insensitive)
    const filterLower = globalFilter.toLowerCase()
    return list.filter((batch) => {
      return Object.values(batch).some((value) => {
        if (value == null) return false
        return String(value).toLowerCase().includes(filterLower)
      })
    })
  })

  return {
    config,
    sortedBatchList,
    sortedFilteredBatchList,
    resetConfig
  }
})
