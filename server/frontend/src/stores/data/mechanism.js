import { defineModule } from './lib/module'

import { api } from '@/api'

export const useMechanism = defineModule({
  name: 'mechanism',
  key: 'ionization_mechanism_id',
  load: {
    method: () =>
      api.http.get(`/ionization_mechanisms`, {
        use: 'read',
        type: 'load_ionization_mechanisms'
      }),
    events: ['ionization_mechanism_reload']
  },
  read: (ionization_mechanism_id) =>
    api.http.get(`/ionization_mechanisms/${ionization_mechanism_id}`),
  create: ({ ionization_mechanism_polarity, ionization_mechanism, reagent }) =>
    api.http.post(
      `/ionization_mechanisms`,
      {
        ionization_mechanism_polarity,
        ionization_mechanism,
        reagent
      },
      {
        use: 'create',
        type: 'create_ionization_mechanism'
      }
    ),
  delete: (ionization_mechanism_id) =>
    api.http.delete(`/ionization_mechanisms/${ionization_mechanism_id}`, {
      use: 'delete',
      type: 'delete_ionization_mechanism'
    })
})
