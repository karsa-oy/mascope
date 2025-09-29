import { defineStore } from 'pinia'

import { api } from '@/api'

import { useData } from '@/lib/store'

export const useInstrument = defineStore('app.data.instrument', () => {
  const name = 'instrument'
  const key = 'instrument'

  const data = useData(
    name,
    () =>
      api.http.get(`/instruments`, {
        use: 'read',
        type: 'load_instruments'
      }),
    {
      key,
      events: ['instruments_reload'],
      selection: {
        mode: 'single',
        persist: true,
        subscribe: true
      }
    }
  )
  return {
    ...data
  }
})
