import { defineStore } from 'pinia'

import { api } from '@/api'

import { useData } from '@/lib/store'

import { useSample } from './sample'

export const usePeak = defineStore('app.data.peak', () => {
  const name = 'peak'
  const key = 'peak_id'

  const data = useData(
    name,
    async ({ sample_item_id }) => {
      if (!sample_item_id) {
        return []
      }
      const data = await api.http.get(`/samples/${sample_item_id}/peaks`, {
        params: {
          areas: true,
          heights: true
        },
        use: 'read',
        type: 'load_sample_peaks'
      })
      if (data) {
        const { peak_id, mz, area, height, target_isotope_formula } = data
        const records = mz.map((mz, i) => ({
          mz: mz,
          peak_id: peak_id[i],
          area: area[i],
          height: height[i],
          target_isotope_formula: target_isotope_formula[i]
        }))
        return records
      } else {
        return []
      }
    },
    {
      key,
      deps: () => ({
        sample_item_id: useSample().focusedId
      }),
      selection: true
    }
  )

  return {
    ...data,
    // api
    computeAll: ({ sample_file_id }) =>
      api.http.get(`/sample/files/${sample_file_id}/peaks/compute`, {
        use: 'read',
        type: 'compute_all_sample_peaks'
      })
  }
})
