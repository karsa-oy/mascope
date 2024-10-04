import { ref, watch } from 'vue'
import { defineStore } from 'pinia'

import { useData } from '../data'

export const useFilter = defineStore('app.ui.filter', () => {
  const data = useData()

  // state
  const mechanism = ref(null)

  // automatically clear filter under certain conditions
  watch(
    () => data.batch.focused,
    (batch) => {
      const batchMechanisms = batch?.build_params?.ionization_mechanisms ?? []
      const noMechanisms = batchMechanisms.length == 0
      const filterMechanismNotInBatch = !(mechanism.value in batchMechanisms)
      if (noMechanisms || filterMechanismNotInBatch) {
        mechanism.value = null
      }
    }
  )

  return {
    mechanism
  }
})
