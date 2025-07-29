import { defineModule } from './lib/module'

import { api } from '@/api'

export const useInstrument = defineModule({
  name: 'instrument',
  key: 'instrument',
  load: {
    method: async () =>
      await api.http.get(`/instruments`, {
        use: 'read',
        type: 'load_instruments'
      }),
    events: ['instruments_reload']
  },
  subscribe: true,
  allowUnfocus: false,
  persist: true
})
