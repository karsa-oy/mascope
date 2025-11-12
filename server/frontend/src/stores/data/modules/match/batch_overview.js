/**
 * Batch overview store for chart visualization.
 *
 * Loads minimal flattened records optimized for trace building:
 * - One record per sample-ion match (valid matches only, match_category > 0)
 * - Flat structure with sample, ion, compound, and match fields
 */

import { defineStore } from 'pinia'

import { api } from '@/api'
import { useData } from '@/lib/store'

import { useBatch } from '../batch'
import { useMatchCollection } from './collection'

export const useMatchBatchOverview = defineStore('app.data.match.batch_overview', () => {
  const name = 'match_batch_overview'
  const key = 'match_ion_id' // unique per sample-ion combination, though not used for selection

  const data = useData(
    name,
    (params) =>
      api.http.get('/match/records/batch_overview', {
        params,
        use: 'read',
        type: 'load_batch_overview_records'
      }),
    {
      key,
      events: ['match_reload'], // Cross-store event (match updates trigger reload)
      deps: () => {
        const batchId = useBatch().focusedId
        const collectionId = useMatchCollection().focusedId

        return {
          sample_batch_id: batchId,
          target_collection_id: collectionId
        }
      }
    }
  )

  return {
    ...data
  }
})
