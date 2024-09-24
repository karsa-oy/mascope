import { api } from '@/api'

import { defineModule } from './lib/module'
import { useSample } from './sample'

export const usePeak = defineModule({
  name: 'peak',
  key: 'peak_id',
  useParent: useSample,
  reloadOn: 'peak_reload',
  load: async ({ sample_file_id }) => {
    const data = (
      await api.request.read({
        method: 'getSamplePeaks',
        body: {
          sample_file_id
        }
      })
    )?.data
    if (data) {
      const { mz, intensity } = data
      const records = mz.map((value, i) => ({
        peak_id: i,
        mz: value,
        intensity: intensity[i]
      }))
      return records
    } else {
      return []
    }
  },
  computeAll: async ({ sample_file_id }) =>
    (
      await api.request.read({
        method: 'computeAllSamplePeaks',
        body: {
          sample_file_id
        }
      })
    )?.data
})
