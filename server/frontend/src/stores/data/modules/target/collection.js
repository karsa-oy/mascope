import { defineStore } from 'pinia'
import { ref } from 'vue'

import { api } from '@/api'
import { useData } from '@/lib/store'

export const useTargetCollection = defineStore('app.data.target.collection', () => {
  const name = 'target_collection'
  const key = 'target_collection_id'

  // Detailed collection data with associations
  const detailed = ref(null)
  const read = (target_collection_id) =>
    api.http.get(`/target/collections/${target_collection_id}`, {
      use: 'read',
      type: 'read_target_collection_details'
    })
  const loadDetailed = async (target_collection_id) => {
    if (!target_collection_id) return null
    console.log(`🗃️ [data ${name}] loading detailed ${target_collection_id}`)
    try {
      detailed.value = await read(target_collection_id)
      return detailed.value
    } catch (error) {
      console.warn(`🗃️ [data ${name}] failed to load detailed ${target_collection_id}: ${error}`)
      detailed.value = null
      return null
    }
  }

  const data = useData(
    name,
    () =>
      api.http.get(`/target/collections`, {
        use: 'read',
        type: 'load_target_collections'
      }),
    {
      key,
      events: ['targets_all_reload'],
      selection: {
        /**
         * Hook to automatically load detailed data when focused
         * and clear when unfocused
         */
        hook: async ({ next, prev }) => {
          if (next) {
            await loadDetailed(next[key])
          } else {
            console.log(`🗃️ [data ${name}] unloading detailed ${prev[key]}`)
            detailed.value = null
          }
        }
      },
      // pass to handle the reloadRecord for list/focused/detailed
      read,
      detailed
    }
  )

  return {
    ...data,
    read,
    loadDetailed,
    // backend methods
    create: (collection) =>
      api.http.post(`/target/collections`, collection, {
        use: 'create',
        type: 'create_target_collection'
      }),
    update: (collection) =>
      api.http.patch(`/target/collections/${collection.target_collection_id}`, collection, {
        use: 'update',
        type: 'update_target_collection'
      }),
    delete: ({ collectionId, deleteOrphanCompounds }) =>
      api.http.delete(`/target/collections/${collectionId}`, {
        params: { delete_orphan_compounds: deleteOrphanCompounds },
        use: 'delete',
        type: 'delete_target_collection'
      })
  }
})
