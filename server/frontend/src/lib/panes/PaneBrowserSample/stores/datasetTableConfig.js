import { ref } from 'vue'
import { defineStore } from 'pinia'

import { FilterMatchMode } from '@primevue/core/api'

export const useDatasetTableConfig = defineStore('browser.sample.datasetTable', () => {
  const config = ref({
    sortField: 'dataset_name',
    sortOrder: 1,
    filters: {
      global: { value: null, matchMode: FilterMatchMode.CONTAINS }
    }
  })

  const defaultConfig = {
    sortField: 'dataset_name',
    sortOrder: 1,
    filters: {
      global: { value: null, matchMode: FilterMatchMode.CONTAINS }
    }
  }

  function resetConfig() {
    config.value = structuredClone(defaultConfig)
  }

  return {
    config,
    resetConfig
  }
})
