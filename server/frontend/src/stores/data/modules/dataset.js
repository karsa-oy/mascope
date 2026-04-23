import { defineStore } from 'pinia'

import { api } from '@/api'

import { useData } from '@/lib/store'

export const useDataset = defineStore('app.data.dataset', () => {
  const name = 'dataset'
  const key = 'dataset_id'

  const data = useData(
    name,
    () =>
      api.http.get(`/datasets`, {
        use: 'read',
        type: 'load_datasets'
      }),
    {
      key,
      selection: {
        mode: 'single',
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
      api.http.post(`/datasets`, dataset, {
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
