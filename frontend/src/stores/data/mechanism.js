import { defineModule } from './lib/module'

import { api } from '@/api'

export const useMechanism = defineModule({
  name: 'mechanism',
  key: 'ionization_mechanism_id',
  load: async () =>
    (
      await api.request.read({
        method: 'getAllIonizationMechanisms'
      })
    )?.data
})
