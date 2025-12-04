import { defineStore } from 'pinia'

import { api } from '@/api'
import { useData } from '@/lib/store'

import { useBatch } from '../batch'
import { useSample } from '../sample'
import { useMatchCollection } from './collection'

export const useMatchIon = defineStore('app.data.match.ion', () => {
  const name = 'match_ion'
  const key = 'target_ion_id'

  const data = useData(
    name,
    (params) =>
      api.http.post(
        '/match/records/ion',
        {
          ...params
        },
        {
          use: 'read',
          type: 'load_match_ion_records'
        }
      ),
    {
      key,
      events: ['match_reload'], // Cross-store event (match updates trigger reload)
      deps: () => {
        const sampleId = useSample().focusedId
        const batchId = useBatch().focusedId
        const collectionId = useMatchCollection().focusedId

        // Add sample/batch parameter based on selection
        return sampleId
          ? { sample_item_ids: [sampleId], target_collection_id: collectionId }
          : { sample_batch_id: batchId, target_collection_id: collectionId }
      },
      selection: { mode: 'multiple' }
    }
  )

  return {
    ...data
  }
})
