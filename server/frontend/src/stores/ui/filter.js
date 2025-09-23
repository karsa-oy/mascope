import { ref, watch } from 'vue'
import { defineStore } from 'pinia'

import { useData } from '../data'

export const useFilter = defineStore('app.ui.filter', () => {
  const data = useData()

  // state
  const mechanism = ref(null)

  // autoremoval of mechanism filters
  watch(
    () => data.batch.focused,
    () => {
      mechanism.value = null
    }
  )

  return {
    mechanism
  }
})
