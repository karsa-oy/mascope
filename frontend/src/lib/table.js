import * as xlsx from 'xlsx'

import { api } from '@/api'

import { useApp } from '@/stores'

import { beautifySnakeCase, strToSnakeCase, genId } from './utils'

export function fromSpreadsheet(text, fields) {
  let lines = text.split(String.fromCharCode(10)).filter((line) => line.length)
  let cols, header, body
  if (!fields) {
    // infer fields from headers
    ;[header, ...body] = lines
    cols = header.split(String.fromCharCode(9)).map((header) => ({
      field: header.toLowerCase().replace(/ /g, '_').trim(),
      label: header
    }))
    fields = cols.map(({ field }) => field)
  } else {
    // use provided fields
    body = lines
    cols = fields.map((field) => ({
      field: field,
      label: beautifySnakeCase(field)
    }))
  }
  // parse rows from the body
  const rows = body
    .map((line) => line.split(String.fromCharCode(9)))
    .map((values) => {
      const cleaned = values.map((val) => val.trim())
      const zipped = cleaned.map((v, i) => [fields[i], v])
      return Object.fromEntries(zipped)
    })
  return {
    cols,
    rows
  }
}
export function toSpreadsheet(filename, sheets) {
  let workbook = xlsx.utils.book_new()
  for (let sheet of sheets) {
    let { rows, cols, name } = sheet
    // construct header
    let fields = cols.map((col) => col.field)
    let headerLabels = cols.map((col) => col.label)
    let header = Object.fromEntries(fields.map((field, index) => [field, headerLabels[index]]))
    // helper function for selecting only used columns
    let selectFields = (row) =>
      Object.fromEntries(Object.entries(row).filter(([field]) => fields.includes(field)))
    // add header and filter out unused fields
    let formattedRows = [header].concat(rows.map(selectFields))
    let worksheet = xlsx.utils.json_to_sheet(formattedRows, {
      // the default header uses field names
      // so we omit since we add our own header
      skipHeader: true
    })
    worksheet = fitColWidths(worksheet)
    xlsx.utils.book_append_sheet(workbook, worksheet, name)
  }
  try {
    xlsx.writeFile(workbook, filename, { type: 'xlsx' })
  } catch (err) {
    console.error(err)
  }
}
function fitColWidths(worksheet) {
  const data = xlsx.utils.sheet_to_json(worksheet)
  if (data.length == 0) return
  const colLengths = Object.keys(data[0]).map((k) => (k ? k.toString().length : 0))
  for (const d of data) {
    Object.values(d).forEach((element, index) => {
      const length = element ? element.toString().length : 0
      if (colLengths[index] < length) {
        colLengths[index] = length
      }
    })
  }
  worksheet['!cols'] = colLengths.map((l) => {
    return {
      wch: l
    }
  })
  return worksheet
}

export function parseAutosamplerCsv(rows) {
  let result = []
  let step = {}
  for (let row of rows) {
    for (let cellKey in row) {
      const [key, value] = row[cellKey].split(':')
      if (key == 'Sequence step' || Object.keys(step).includes('Sequence step')) {
        // New sequence step or append existing step
        if (key && key.length) {
          step[key.trim()] = value.trim()
        }
      }
    }
    if (Object.keys(step).includes('Presence')) {
      // Sequence step complete
      result.push(...parseStep(step))
      step = {}
    }
  }
  return result

  function parseStep(step) {
    let result = []
    const cycles = step['Cycle(s)']
    delete step['Cycle(s)']
    for (let i = 0; i < cycles; ++i) {
      result.push(step)
    }
    return result
  }
}

export function parseGenericCsv(cols, rows) {
  // Filter out rows where sample name is empty or None
  const validRows = rows.filter((row) => row[cols[0].field] && row[cols[0].field].trim() !== '')

  // Map over the filtered non-empty rows
  return validRows.map((row) => {
    // Determine if filter_id should be generated
    const checkTypesToGenerateFilterId = !['INSTRUMENT_BACKGROUND', 'ONLINE'].includes(
      row[cols[1].field]
    )

    const newSampleItem = {
      sample_item_name: row[cols[0].field],
      sample_item_type: row[cols[1].field] ? row[cols[1].field].trim() : 'UNKNOWN',
      // Generate filter_id only if the type is not "INSTRUMENT_BACKGROUND" or "ONLINE", for "INSTRUMENT_BACKGROUND" or "ONLINE" set filter_id to null
      filter_id: checkTypesToGenerateFilterId ? row[cols[2].field] || genId(6, false) : null,
      sample_item_attributes: {}
    }

    // Process the rest of the columns for sample_item_attributes
    cols.slice(3).forEach((col) => {
      const attrKey = strToSnakeCase(col.label.trim())
      // Ensure that if the attribute is empty, we set it to a default or empty string
      newSampleItem.sample_item_attributes[attrKey] =
        col.field && row[col.field].trim() ? row[col.field].trim() : ''
    })
    return newSampleItem
  })
}

/*
 *  Compare records or record arrays by a field
 *
 *  e.g. equals(app.data.workspace.list, selected.workspaces, workspace_id)
 *  will check that the selected workspace ids match those in the store
 *  and equals(app.data.sample.focused, selected.sample, sample_item_id) will
 *  check that the selected sample has the same id as the active one.
 */
export function equals(first, second, field) {
  const nullish = (input) => input == (undefined || null)
  if (nullish(first) || nullish(second)) {
    return first == second
  }
  if (Array.isArray(first) && Array.isArray(second)) {
    return (
      first
        .map((row) => row[field])
        .sort()
        .join() ==
      second
        .map((row) => row[field])
        .sort()
        .join()
    )
  }
  if (typeof first == 'object' && typeof second == 'object') {
    return first[field] == second[field]
  }
}

/**
 * Exports the sample batch and associated match data to an Excel spreadsheet.
 *
 * This function gathers data from the focused sample batch, including the batch details,
 * samples, and match data for compounds and ions. The data is then formatted into multiple sheets
 * within an Excel workbook and saved as a file.
 *
 * Steps:
 * 1. Verifies that a batch is currently focused; if not, logs an error and exits.
 * 2. Fetches detailed match data and batch parameters for the focused batch using API calls.
 * 3. Structures the batch, sample, compound, and ion data into rows and columns for Excel sheets.
 * 4. Generates a filename using the current date and time, ensuring a unique file name.
 * 5. Calls `toSpreadsheet` to create and save the Excel file with the collected data.
 *
 * @async
 * @function batchExportCsv
 * @returns {Promise<void>} - This function does not return a value but triggers a file download.
 */
export async function batchExportCsv() {
  const app = useApp()

  if (!app.data.batch.focused) {
    console.error('No batch is currently focused.')
    return
  }

  const focusedBatch = app.data.batch.focused
  const batchMatchData = await app.data.batch.aggregateBatchMatches(focusedBatch)
  const batch = batchMatchData.sample_batch

  const samples = (
    await api.request.read({
      method: 'getAllSamples',
      body: {
        sample_batch_id: focusedBatch.sample_batch_id,
        sort: 'datetime_utc'
      }
    })
  )?.data

  // Lookup the calibration collection name
  const calibrationCollectionName =
    app.data.target.collection.list.find(
      (collection) => collection.target_collection_id === batch.build_params.calibration_collection
    )?.target_collection_name || batch.build_params.calibration_collection

  // Lookup the ion mechanism names
  const ionMechanismNames = (batch.build_params.ion_mechanisms || [])
    .map(
      (id) =>
        app.data.mechanism.list.find((mechanism) => mechanism.ionization_mechanism_id === id)
          ?.ionization_mechanism
    )
    .filter(Boolean)
    .join(', ')

  const batchCols = [
    { field: 'field', label: 'Batch' },
    { field: 'value', label: '' }
  ]

  const batchRows = [
    { field: 'Name', value: batch.sample_batch_name },
    { field: 'Description', value: batch.sample_batch_description },
    { field: 'Workspace', value: app.data.workspace.focused?.workspace_name || 'N/A' },
    { field: '', value: '' },
    {
      field: 'Target collections',
      value:
        app.data.match.collection.list?.map((row) => row.target_collection_name).join(', ') ??
        'none'
    },
    { field: '', value: '' },
    { field: 'Parameters', value: '' },
    { field: 'Calibration collection', value: calibrationCollectionName },
    { field: 'Ion mechanisms', value: ionMechanismNames }
  ]

  const sampleItemCols = [
    { field: 'sample_item_name', label: 'Sample name' },
    { field: 'filename', label: 'Filename' },
    { field: 'datetime', label: 'Datetime' },
    { field: 'sample_item_type', label: 'Sample type' },
    { field: 'tic', label: 'TIC' },
    { field: 'filter_id', label: 'Filter ID' },
    { field: 'match_score', label: 'Match score' }
  ]

  const matchCompoundCols = [
    { field: 'sample_item_name', label: 'Sample name' },
    { field: 'filename', label: 'Filename' },
    { field: 'sample_item_type', label: 'Sample type' },
    { field: 'target_compound_name', label: 'Compound name' },
    { field: 'target_compound_formula', label: 'Compound formula' },
    { field: 'sample_peak_area_sum', label: 'Sample peak intensity' },
    { field: 'sample_peak_interference_sum', label: 'Sample peak interference' },
    { field: 'match_score', label: 'Match score' }
  ]

  const matchIonCols = [
    { field: 'sample_item_name', label: 'Sample name' },
    { field: 'filename', label: 'Filename' },
    { field: 'sample_item_type', label: 'Sample type' },
    { field: 'target_compound_name', label: 'Compound name' },
    { field: 'target_compound_formula', label: 'Compound formula' },
    { field: 'target_ion_mechanism', label: 'Ionization mechanism' },
    { field: 'target_ion_formula', label: 'Ion formula' },
    { field: 'sample_peak_area_sum', label: 'Sample peak intensity' },
    { field: 'sample_peak_interference_sum', label: 'Sample peak interference' },
    { field: 'match_score', label: 'Match score' }
  ]

  const datetimestamp = new Date().toJSON().slice(0, -5).replace(/[-:]/g, '')
  const filename = `${datetimestamp}_${batch.sample_batch_name.replaceAll(' ', '_')}.xlsx`

  toSpreadsheet(filename, [
    {
      name: 'Batch',
      rows: batchRows,
      cols: batchCols
    },
    {
      name: 'Samples',
      rows: samples,
      cols: sampleItemCols
    },
    {
      name: 'Match compounds',
      rows: batchMatchData.match_compounds,
      cols: matchCompoundCols
    },
    {
      name: 'Match ions',
      rows: batchMatchData.match_ions,
      cols: matchIonCols
    }
  ])
}
