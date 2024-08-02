import { defineModule } from './lib/module'

import { api } from '@/api'

import { useMzFit } from '@/lib/mzFit'

import { useWorkspace } from './workspace'

export const useBatch = defineModule({
  name: 'batch',
  key: 'sample_batch_id',
  useParent: useWorkspace,
  subscribe: true,
  reloadSelfOn: 'sample_batch_reload',
  reloadChildrenOn: 'sample_batch_reload',
  load: async (workspace_id) =>
    (
      await api.request.read({
        method: 'getAllBatches',
        body: { workspace_id },
        errorMessage: `Failed to load the workspace batches.`
      })
    ).data,
  read: async (sample_batch_id) =>
    await api.request.read({
      method: 'getBatch',
      body: { batchId: sample_batch_id }
    }),
  create: async (batch) =>
    await api.request.create({
      method: 'createBatch',
      body: batch
    }),
  update: async (batch) =>
    await api.request.update({
      method: 'updateBatch',
      body: {
        batchId: batch.sample_batch_id,
        body: batch
      }
    }),
  delete: async (batch) =>
    await api.request.process({
      method: 'deleteBatch',
      body: batch
    }),
  copy: async ({ sample_batch_id, workspace_id, sample_batch_name, sample_batch_description }) =>
    await api.request.process({
      method: 'copySampleBatch',
      body: {
        batchId: sample_batch_id,
        body: {
          workspace_id,
          sample_batch_name,
          sample_batch_description
        }
      }
    }),
  importSamples: async ({ batch, sample_items }) => {
    const mzFit = useMzFit()
    return await api.request.process({
      method: 'importSamplesToBatch',
      body: {
        batch,
        body: {
          sample_items,
          params: mzFit.params
        }
      }
    })
  },
  rematch: async ({ sample_batch_id }) =>
    await api.request.process({
      method: 'rematchBatch',
      body: { batchId: sample_batch_id }
    }),
  exportPeaks: async ({ sample_batch_id }) =>
    await api.request.process({
      method: 'batchExportPeakData',
      body: { sample_batch_id }
    })
})
