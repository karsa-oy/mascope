import { defineModule } from './lib/module'

import { api } from '@/api'

export const useTargetCollection = defineModule({
  name: 'target_collection',
  key: 'target_collection_id',
  reloadOn: 'targets_all_reload',
  load: () =>
    api.http.get(`/target/collections`, {
      use: 'read',
      type: 'load_target_collectoons'
    }),
  read: (target_collection_id) =>
    api.http.get(`/target/collections/${target_collection_id}`, {
      use: 'read',
      type: 'load_target_collectoons'
    }),
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
  delete: ({ collectionId }) =>
    api.http.delete(`/target/collections/${collectionId}`, {
      use: 'delete',
      type: 'delete_target_collection'
    })
})

export const useTargetCompound = defineModule({
  name: 'target_compound',
  key: 'target_compound_id',
  reloadOn: 'targets_all_reload',
  load: () =>
    api.http.get(`/target/compounds`, {
      use: 'read',
      type: 'read_target_compounds'
    })
})
