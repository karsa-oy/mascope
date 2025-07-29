import { api } from '@/api'

import { defineModule } from './lib/module'
import { useSample } from './sample'

export const usePeak = defineModule({
  name: 'peak',
  key: 'mz',
  load: {
    parent: useSample,
    method: async ({ sample_item_id }) => {
      const data = await api.http.get(`/samples/${sample_item_id}/peaks`, {
        params: {
          areas: true,
          heights: true
        },
        use: 'read',
        type: 'load_sample_peaks'
      })
      if (data) {
        const { mz, area, height } = data
        const records = mz.map((mz, i) => ({
          mz: mz,
          area: area[i],
          height: height[i]
        }))
        return records
      } else {
        return []
      }
    },
    events: ['peak_reload']
  },
  computeAll: ({ sample_file_id }) =>
    api.http.get(`/sample/files/${sample_file_id}/peaks/compute`, {
      use: 'read',
      type: 'compute_all_sample_peaks'
    })
})
