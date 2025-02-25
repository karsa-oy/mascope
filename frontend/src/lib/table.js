import * as xlsx from 'xlsx'

import { beautifySnakeCase } from './utils'

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
