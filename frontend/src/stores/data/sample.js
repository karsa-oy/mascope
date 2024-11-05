import { defineModule } from './lib/module'

import { api } from '@/api'

import { useMzFit } from '@/lib/mzFit'

import { useBatch } from './batch'

export const useSample = defineModule({
  name: 'sample',
  key: 'sample_item_id',
  multiselect: true,
  useParent: useBatch,
  unfocusBefore: ['delete'],
  subscribe: ({ sample_file_id }) => sample_file_id,
  load: async ({ sample_batch_id }) =>
    (
      await api.request.read({
        method: 'getBatchSamples',
        body: {
          sample_batch_id,
          sort: 'datetime_utc'
        }
      })
    )?.data,
  read: async () => {
    // TODO
  },
  create: async (sample) =>
    await api.request.create({
      method: 'createSample',
      body: sample
    }),
  update: async (sample) =>
    await api.request.update({
      method: 'updateSample',
      body: { sampleId: sample.sample_item_id, body: sample }
    }),
  delete: async ({ sample_item_id }) => {
    return await api.request.delete({
      method: 'deleteSample',
      body: { sampleId: sample_item_id }
    })
  },
  upload: async (files) => {
    return await api.request.upload({
      method: 'uploadSampleFile',
      files: files
    })
  },
  copy: async ({ sample_item_id, sample_batch_id, sample_item_name }) =>
    await api.request.process({
      method: 'copySample',
      body: {
        sampleId: sample_item_id,
        body: {
          sample_batch_id: sample_batch_id,
          sample_item_name: sample_item_name
        }
      }
    }),
  process: async (sample) => {
    const mzFit = useMzFit()
    return await api.request.process({
      method: 'processSample',
      body: {
        sample,
        mz_calibration_params: mzFit.mzCalibrationParams
      }
    })
  },
  match: async ({ sample_item_id }) =>
    await api.request.process({
      method: 'matchSampleCompute',
      body: { sampleId: sample_item_id }
    }),
  rematch: async ({ sample_item_id }) =>
    await api.request.process({
      method: 'rematchSample',
      body: { sampleId: sample_item_id }
    })
})
