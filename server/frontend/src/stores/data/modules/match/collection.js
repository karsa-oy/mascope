import { defineStore } from 'pinia'

import { api } from '@/api'
import { useData } from '@/lib/store'

import { useBatch } from '../batch'
import { useSample } from '../sample'
import { useTargetCollection } from '../target/collection'

export const useMatchCollection = defineStore('app.data.match.collection', () => {
  const name = 'match_collection'
  const key = 'target_collection_id'

  const data = useData(
    name,
    (params) =>
      api.http.get('/match/records/collection', {
        params,
        use: 'read',
        type: 'load_match_collection_records'
      }),
    {
      key,
      events: ['match_reload', 'collection_reload'],
      deps: () => {
        const sampleId = useSample().focusedId
        const batchId = useBatch().focusedId

        // Conditional loading: sample-level if sample selected, else batch-level
        return sampleId ? { sample_item_id: sampleId } : { sample_batch_id: batchId }
      },
      selection: {
        /**
         * Cross-store sync: focus target collection when match collection focused
         */
        hook: async ({ next, prev }) => {
          const targetCollection = useTargetCollection()

          if (next) {
            console.log(`🔗 [selection ${name}] cross-store sync: focusing collection ${next[key]}`)
            const target = targetCollection.list.find((c) => c[key] === next[key])
            // Focus in target store (target collection's own hook will handle detailed loading)
            target
              ? targetCollection.focus(target)
              : console.warn(
                  `🔗 [selection ${name}] Collection ${next[key]} not found in target store`
                )
          } else if (prev && !next) {
            // Unfocus target collection when match collection is unfocused
            console.log(`🔗 [selection ${name}] cross-store sync: unfocusing target collection`)
            targetCollection.unfocus()
          }
        }
      }
    }
  )

  return {
    ...data
  }
})
