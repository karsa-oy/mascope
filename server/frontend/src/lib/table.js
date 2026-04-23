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
/*
 *  Compare records or record arrays by a field
 *
 *  e.g. equals(app.data.dataset.list, selected.datasets, dataset_id)
 *  will check that the selected dataset ids match those in the store
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
