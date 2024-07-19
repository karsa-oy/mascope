import { watch, computed } from 'vue'

import { api } from '@/api'

import { defineModule } from './lib'

import { useBatch } from './batch'
import { useSample } from './sample'

const defineMatch = (level) =>
  defineModule({
    name: `match.${level.toLowerCase()}`,
    key: `match_${level.toLowerCase()}_id`,
    useParent: () => ({
      // 'virtual' parent ensures matches react
      // to batch and sample selections
      name: 'batch & sample',
      multiselect: false,
      register: ({ reload }) => {
        watch(
          computed(() => {
            const batch = useBatch()
            const sample = useSample()
            return sample.focused?.sample_item_id ?? batch.focused?.sample_batch_id
          }),
          () => reload()
        )
      }
    }),
    load: async (focusedId) => {
      const batch = useBatch()
      const sample = useSample()
      if (sample.focused) {
        // If a sample is focused, load sample level matches
        return (
          await api.request.read({
            method: `getSampleMatch${level}s`,
            body: {
              sample_item_id: sample.focused.sample_item_id
            }
          })
        ).data
      } else if (batch.focused) {
        // If a batch is focused, load batch level matches
        return (
          await api.request.read({
            method: `getBatchMatch${level}s`,
            body: {
              sample_batch_id: batch.focused.sample_batch_id
            }
          })
        ).data
      } else {
        // Otherwise unload the data
        return []
      }
    }
  })

export const useMatchCollection = defineMatch('Collection')
export const useMatchCompound = defineMatch('Compound')
export const useMatchIon = defineMatch('Ion')
export const useMatchIsotope = defineMatch('Isotope')
