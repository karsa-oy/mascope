import { ref, watch } from 'vue'
import { defineStore } from 'pinia'

import { useData } from '../data'

export const useFilter = defineStore('app.ui.filter', () => {
  const data = useData()

  // state
  const mechanism = ref(null)

  // autoremoval of mechanism filters
  watch(
    () => data.batch.focused?.build_params?.ionization_mechanisms ?? [],
    (batchMechanisms) => {
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
