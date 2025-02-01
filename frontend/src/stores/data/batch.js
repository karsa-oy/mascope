import { defineModule } from './lib/module'

import { api } from '@/api'

import { useMzFit } from '@/lib/mzFit'

import { useUi } from '../ui'

import { useWorkspace } from './workspace'
import { useSample } from './sample'

export const useBatch = defineModule({
  name: 'batch',
  key: 'sample_batch_id',
  useParent: useWorkspace,
  subscribe: true,
  reloadOn: 'sample_batch_reload',
  onRefocus: () => {
    const sample = useSample()
    const ui = useUi()
    if (sample.list.length > 0) {
      ui.tab.active = 'batch'
    } else if (ui.tab.active == 'batch') {
      ui.tab.default()
    }
  },
  onEvent: () => {
    const sample = useSample()
    const ui = useUi()
    if (sample.list.length == 0 && ui.tab.active == 'batch') {
      ui.tab.default()
    }
  },
  load: ({ workspace_id }) =>
    api.http.get(`/sample/batches`, {
      params: { workspace_id },
      use: 'read',
      type: 'load_batches'
    }),
  read: (sample_batch_id) =>
    api.http.get(`/sample/batches/${sample_batch_id}`, {
      use: 'read',
      type: 'read_batch'
    }),
  create: (batch) =>
    api.http.post(`/sample/batches/`, batch, {
      use: 'create',
      type: 'create_batch'
    }),
  update: (batch) =>
    api.http.patch(`/sample/batches/${batch.sample_batch_id}`, batch, {
      use: 'update',
      type: 'update_batch'
    }),
  delete: ({ sample_batch_id }) =>
    api.http.delete(`/sample/batches/${sample_batch_id}`, {
      use: 'process',
      type: 'delete_batch'
    }),
  copy: ({ sample_batch_id, workspace_id, sample_batch_name, sample_batch_description }) =>
    api.http.post(
      `/sample/batches/${sample_batch_id}/copy`,
      {
        workspace_id,
        sample_batch_name,
        sample_batch_description
      },
      {
        use: 'process',
        type: 'copy_batch'
      }
    ),
  importSamples: async ({ batch, sample_items, instrument_config }) => {
    const mzFit = useMzFit()
    return await api.http.post(
      `/sample/batches/${batch.sample_batch_id}/import`,
      {
        sample_items,
        mz_calibration_params: mzFit.mzCalibrationParams,
        instrument_config
      },
      {
        use: 'process',
        type: 'import_samples'
      }
    )
  },
  rematch: ({ sample_batch_id }) =>
    api.http.post(
      `/match/rematch/batch/${sample_batch_id}`,
      {},
      {
        use: 'process',
        type: 'rematch_batch'
      }
    ),
  aggregateBatchMatches: ({ sample_batch_id }) =>
    api.http.get(`/match/aggregate/batch/${sample_batch_id}/all`, {
      use: 'process',
      type: 'aggregate_batch_matches'
    }),
  exportPeaks: async ({ sample_batch_id }) =>
    api.http.get(`/sample/batches/${sample_batch_id}/export_peaks`, {
      use: 'process',
      type: 'export_batch_peaks'
    })
})
