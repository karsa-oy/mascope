import { ref, computed } from 'vue'
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

  const isDefault = computed(() => JSON.stringify(config.value) === JSON.stringify(defaultConfig))

  function resetConfig() {
    config.value = { ...defaultConfig }
  }

  return {
    config,
    resetConfig
  }
})
