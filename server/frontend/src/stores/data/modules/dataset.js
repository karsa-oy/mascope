import { defineStore } from 'pinia'

import { api } from '@/api'

import { useData } from '@/lib/store'
import { useWorkspace } from './workspace'

export const useDataset = defineStore('app.data.dataset', () => {
  const name = 'dataset'
  const key = 'dataset_id'

  const data = useData(
    name,
    ({ workspace_id }) =>
      api.http.get(`/workspaces/${workspace_id}/datasets`, {
        use: 'read',
        type: 'load_datasets'
      }),
    {
      key,
      deps: () => ({
        workspace_id: useWorkspace().focusedId
      }),
      selection: {
        mode: 'binary',
        subscribe: true,
        persist: true
      },
      read: (dataset_id) =>
        api.http.get(`/datasets/${dataset_id}`, {
          use: 'read',
          type: 'read_dataset'
        })
    }
  )

  return {
    ...data,
    // backend
    create: (dataset) =>
      api.http.post(`/workspaces/${useWorkspace().focusedId}/datasets`, dataset, {
        use: 'create',
        type: 'create_dataset'
      }),
    update: (dataset) =>
      api.http.patch(`/datasets/${dataset.dataset_id}`, dataset, {
        use: 'update',
        type: 'update_dataset'
      }),
    delete: (dataset) =>
      api.http.delete(`/datasets/${dataset.dataset_id}`, {
        use: 'delete',
        type: 'delete_dataset'
      })
  }
})
