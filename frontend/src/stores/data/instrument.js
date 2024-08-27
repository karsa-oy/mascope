import { defineModule } from './lib/module'

import { api, extractDistinctValues } from '@/api'

export const useInstrument = defineModule({
  name: 'instrument',
  key: 'instrument',
  subscribe: true,
  load: async () =>
    await api.request
      .read({
        method: 'getAllInstrumentFunctions'
      })
      .then((res) => extractDistinctValues(res.data, 'instrument'))
})
