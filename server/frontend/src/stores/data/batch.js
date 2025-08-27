import { defineModule } from './lib/module'

import { api } from '@/api'

import { useMzFit } from '@/lib/mzFit'
import { toSpreadsheet } from '@/lib/table'

import { useUi } from '../ui'

import { useWorkspace } from './workspace'
import { useSample } from './sample'
import { useTargetCollection } from './target'
import { useMatchCollection } from './match'
import { useMechanism } from './mechanism'
import { useAcquisition } from './acquisition'

export const useBatch = defineModule({
  name: 'batch',
  key: 'sample_batch_id',
  selection: {
    subscribe: true,
    hook: () => {
      const sample = useSample()
      const ui = useUi()
      const acquistion = useAcquisition()
      if (sample.list.length > 0) {
        if (acquistion.selected.length === 0) {
          ui.tab.active = 'batch'
        }
      } else if (ui.tab.active == 'batch') {
        ui.tab.default()
      }
    }
  },
  load: {
    parent: useWorkspace,
    method: ({ workspace_id }) =>
      api.http.get(`/sample/batches`, {
        params: { workspace_id },
        use: 'read',
        type: 'load_batches'
      }),
    events: ['sample_batch_reload'],
    hook: () => {
      const sample = useSample()
      const ui = useUi()
      if (sample.list.length == 0 && ui.tab.active == 'batch') {
        ui.tab.default()
      }
    }
  },
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
  exportPeaks: async ({ sample_batch_id }) =>
    api.http.get(`/sample/batches/${sample_batch_id}/export_peaks`, {
      use: 'process',
      type: 'export_batch_peaks'
    }),
  /**
   * Exports the sample batch and associated match data to an Excel spreadsheet.
   *
   * This function gathers data from the focused sample batch, including the batch details,
   * samples, and match data for compounds and ions. The data is then formatted into multiple sheets
   * within an Excel workbook and saved as a file.
   *
   * @async
   * @function batchExportCsv
   * @returns {Promise<void>} - This function does not return a value but triggers a file download.
   */
  exportCsv: async ({ sample_batch_id }) => {
    const targetCollection = useTargetCollection()
    const workspace = useWorkspace()
    const matchCollection = useMatchCollection()
    const mechanism = useMechanism()

    if (!sample_batch_id) {
      console.error('📄 [export] no sample batch ID provided.')
      return
    }

    const matches = await api.http.get(`/match/aggregate/batch/${sample_batch_id}/all`, {
      use: 'read',
      type: 'aggregate_batch_matches'
    })
    const batch = matches.sample_batch

    const samples = await api.http.get(`/samples`, {
      params: {
        sample_batch_id,
        sort: 'datetime_utc'
      },
      use: 'read',
      type: 'load_samples'
    })

    const datetimestamp = new Date().toJSON().slice(0, -5).replace(/[-:]/g, '')
    const filename = `${datetimestamp}_${batch.sample_batch_name.replaceAll(' ', '_')}.xlsx`

    toSpreadsheet(filename, [
      {
        name: 'Batch',
        rows: [
          { field: 'Name', value: batch.sample_batch_name },
          { field: 'Description', value: batch.sample_batch_description },
          { field: 'Workspace', value: workspace.focused?.workspace_name || 'N/A' },
          { field: '', value: '' },
          {
            field: 'Target collections',
            value:
              matchCollection.list?.map((row) => row.target_collection_name).join(', ') ?? 'none'
          },
          { field: '', value: '' },
          { field: 'Parameters', value: '' },
          {
            field: 'Calibration collection',
            value:
              targetCollection.list.find(
                (coll) => coll.target_collection_id === batch.build_params.calibration_collection
              )?.target_collection_name ?? batch.build_params.calibration_collection
          },
          {
            field: 'Ion mechanisms',
            value: (batch.build_params.ion_mechanisms ?? [])
              .map(
                (id) =>
                  mechanism.list.find((mechanism) => mechanism.ionization_mechanism_id === id)
                    ?.ionization_mechanism
              )
              .filter(Boolean)
              .join(', ')
          }
        ],
        cols: [
          { field: 'field', label: 'Batch' },
          { field: 'value', label: '' }
        ]
      },
      {
        name: 'Samples',
        rows: samples,
        cols: [
          { field: 'sample_item_name', label: 'Sample name' },
          { field: 'filename', label: 'Filename' },
          { field: 'datetime', label: 'Datetime' },
          { field: 'sample_item_type', label: 'Sample type' },
          { field: 'tic', label: 'TIC' },
          { field: 'filter_id', label: 'Filter ID' },
          { field: 'match_score', label: 'Match score' }
        ]
      },
      {
        name: 'Match compounds',
        rows: matches.match_compounds,
        cols: [
          { field: 'sample_item_name', label: 'Sample name' },
          { field: 'filename', label: 'Filename' },
          { field: 'sample_item_type', label: 'Sample type' },
          { field: 'target_compound_name', label: 'Compound name' },
          { field: 'target_compound_formula', label: 'Compound formula' },
          { field: 'sample_peak_intensity_sum', label: 'Total peak intensity (cps)' },
          { field: 'match_score', label: 'Match score' }
        ]
      },
      {
        name: 'Match ions',
        rows: matches.match_ions,
        cols: [
          { field: 'sample_item_name', label: 'Sample name' },
          { field: 'filename', label: 'Filename' },
          { field: 'sample_item_type', label: 'Sample type' },
          { field: 'target_compound_name', label: 'Compound name' },
          { field: 'target_compound_formula', label: 'Compound formula' },
          { field: 'ionization_mechanism', label: 'Ionization mechanism' },
          { field: 'target_ion_formula', label: 'Ion formula' },
          { field: 'sample_peak_intensity_sum', label: 'Total peak intensity (cps)' },
          { field: 'match_score', label: 'Match score' }
        ]
      }
    ])
  }
})
