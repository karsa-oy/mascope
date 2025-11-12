import { defineStore } from 'pinia'

import { api } from '@/api'
import { useData } from '@/lib/store'

export const useTargetCompound = defineStore('app.data.target.compound', () => {
  const name = 'target_compound'

  const data = useData(name, () =>
    api.http.get(`/target/compounds`, {
      use: 'read',
      type: 'load_target_compounds'
    })
  )

  return {
    ...data,
    // backend methods
    update: (compound) =>
      api.http.patch(`/target/compounds/`, [compound], {
        use: 'update',
        type: 'update_target_compound'
      })
  }
})
