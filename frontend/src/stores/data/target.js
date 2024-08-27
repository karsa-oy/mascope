import { defineModule } from './lib/module'

import { api } from '@/api'

export const useTargetCollection = defineModule({
  name: 'target_collection',
  key: 'target_collection_id',
  reloadOn: 'targets_all_reload',
  load: async () =>
    (
      await api.request.read({
        method: 'getAllTargetCollections'
      })
    )?.data,
  read: async (target_collection_id) =>
    await api.request.read({
      method: 'getTargetCollection',
      body: target_collection_id
    }),
  create: async (collection) =>
    await api.request.create({
      method: 'createTargetCollection',
      body: collection
    }),
  update: async (collection) =>
    await api.request.update({
      method: 'updateTargetCollection',
      body: {
        collectionId: collection.target_collection_id,
        body: collection
      }
    }),
  delete: async ({ collectionId, collectionName, deleteOrphanCompounds }) =>
    await api.request.delete({
      method: 'deleteTargetCollection',
      body: { collectionId, collectionName, deleteOrphanCompounds }
    })
})

export const useTargetCompound = defineModule({
  name: 'target_compound',
  key: 'target_compound_id',
  reloadOn: 'targets_all_reload',
  load: async () =>
    (
      await api.request.read({
        method: 'getAllTargetCompounds',
        body: {}
      })
    )?.data,
  read: async () => {
    // TODO
  }
})
