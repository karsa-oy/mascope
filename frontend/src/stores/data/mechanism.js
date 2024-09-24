import { defineModule } from './lib/module'

import { api } from '@/api'

export const useMechanism = defineModule({
  name: 'mechanism',
  key: 'ionization_mechanism_id',
  reloadOn: 'ionization_mechanism_reload',
  load: async () =>
    (
      await api.request.read({
        method: 'getAllIonizationMechanisms'
      })
    )?.data,
  read: async (ionization_mechanism_id) =>
    (
      await api.request.read({
        method: 'getIonizationMechanism',
        body: ionization_mechanism_id
      })
    )?.data,
  create: async ({ ionization_mechanism_polarity, ionization_mechanism, reagent }) =>
    (
      await api.request.create({
        method: 'createIonizationMechanism',
        body: {
          ionization_mechanism_polarity,
          ionization_mechanism,
          reagent
        }
      })
    )?.data,
  delete: async (ionization_mechanism_id) =>
    (
      await api.request.delete({
        method: 'deleteIonizationMechanism',
        body: ionization_mechanism_id
      })
    )?.data
})
