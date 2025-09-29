import { defineStore } from 'pinia'

import { api } from '@/api'
import { useData } from '@/lib/store'

export const useIonizationMode = defineStore('app.data.ionization.mode', () => {
  const name = 'ionization_mode'
  const key = 'ionization_mode_id'

  const data = useData(
    name,
    () =>
      api.http.get(`/ionization/modes`, {
        use: 'read',
        type: 'load_ionization_modes'
      }),
    {
      key,
      events: ['ionization_mode_reload']
    }
  )

  return {
    ...data,
    // api
    read: (ionization_mode_id) =>
      api.http.get(`/ionization/modes/${ionization_mode_id}`, {
        use: 'read',
        type: 'read_ionization_mode'
      }),
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
    update: (ionization_mode_id, ionization_mode_update) =>
      api.http.patch(`/ionization/modes/${ionization_mode_id}`, ionization_mode_update, {
        use: 'update',
        type: 'update_ionization_mode'
      }),
    delete: (ionization_mode_id) =>
      api.http.delete(`/ionization/modes/${ionization_mode_id}`, {
        use: 'delete',
        type: 'delete_ionization_mode'
      })
  }
})
