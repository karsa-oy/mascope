import { ref, reactive } from 'vue'

import { api } from '@/api'

export const useInstrumentFunction = () => {
  const list = ref([])

  async function load({
    // query parameters
    instrument = null,
    method_file = null,
    sort = null,
    order = null
  }) {
    list.value = await api.http.get(`/instrument_functions`, {
      params: {
        instrument,
        method_file,
        sort,
        order
      },
      use: 'read',
      type: 'load_instrument_functions'
    })
  }

  return reactive({
    // state
    list,
    // actions
    load
  })
}
