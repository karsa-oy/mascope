import { defineModule } from './lib/module'

import { api } from '@/api'

export const useIonizationMechanism = defineModule({
  name: 'ionization_mechanism',
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

export const useIonizationMode = defineModule({
  name: 'ionization_mode',
  key: 'ionization_mode_id',
  load: {
    method: () =>
      api.http.get(`/ionization/modes`, {
        use: 'read',
        type: 'load_ionization_modes'
      }),
    events: ['ionization_mode_reload']
  },
  read: (ionization_mode_id) => api.http.get(`/ionization/modes/${ionization_mode_id}`),
  create: ({
    ionization_mode_name,
    ionization_mode_token,
    ionization_mode_polarity,
    ionization_mechanism_ids,
    calibration_collection_id,
    diagnostic_collection_id
  }) =>
    api.http.post(
      `/ionization/modes`,
      {
        ionization_mode_name,
        ionization_mode_token,
        ionization_mode_polarity,
        ionization_mechanism_ids,
        calibration_collection_id,
        diagnostic_collection_id
      },
      {
        use: 'create',
        type: 'create_ionization_mode'
      }
    ),
  update: (ionization_mode) =>
    api.http.patch(`/ionization/modes/${ionization_mode.ionization_mode_id}`, ionization_mode, {
      use: 'update',
      type: 'update_ionization_mode'
    }),
  delete: (ionization_mode_id) =>
    api.http.delete(`/ionization/modes/${ionization_mode_id}`, {
      use: 'delete',
      type: 'delete_ionization_mode'
    })
})
