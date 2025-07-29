import { defineModule } from './lib/module'

import { api } from '@/api'

export const useInstrument = defineModule({
  name: 'instrument',
  key: 'instrument',
  selection: {
    mode: 'single',
    persist: true,
    subscribe: true
  },
  load: {
    method: async () =>
      await api.http.get(`/instruments`, {
        use: 'read',
        type: 'load_instruments'
      }),
    events: ['instruments_reload']
  }
})
