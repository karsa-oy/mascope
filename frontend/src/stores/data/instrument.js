import { defineModule } from './lib/module'

import { api, extractDistinctValues } from '@/api'

export const useInstrument = defineModule({
  name: 'instrument',
  key: 'instrument',
  subscribe: true,
  load: async () =>
    await api.http
      .get(`/instrument_functions`, {
        use: 'read',
        type: 'load_instruments'
      })
      .then((data) => extractDistinctValues(data, 'instrument'))
})
