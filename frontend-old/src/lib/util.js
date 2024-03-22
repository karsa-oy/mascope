import { customAlphabet } from 'nanoid'

// ==== String manipulation functions ====

export function beautifySnakeCase(str) {
  // Replace underscores with white space and capitalize first letter
  return capitalizeFirstLetter(str.replaceAll('_', ' '))
}

export function strToSnakeCase(str) {
  // Convert any string to snake_case
  return str
    .replace(/\W+/g, ' ')
    .split(/ |\B(?=[A-Z])/)
    .map((word) => word.toLowerCase())
    .join('_')
}

export function capitalizeFirstLetter(str) {
  // Capitalize first letter of a string
  return str[0].toUpperCase() + str.slice(1)
}

// ==== End string manipulation functions ====

export function genId(len, case_sensitive = true) {
  if (case_sensitive) {
    var alphabet = '0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz'
  } else {
    var alphabet = '0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ'
  }
  const nanoid = customAlphabet(alphabet, len)
  return nanoid()
}

export function parseAutosamplerCsv(rows) {
  function explodeSequenceStep(step) {
    let result = []
    const cycles = step['Cycle(s)']
    delete step['Cycle(s)']
    for (let i = 0; i < cycles; ++i) {
      result.push(step)
    }
    return result
  }
  let result = []
  var sequenceStep = {}
  for (let row of rows) {
    for (let cellKey in row) {
      const [key, value] = row[cellKey].split(':')
      if (key == 'Sequence step' || Object.keys(sequenceStep).includes('Sequence step')) {
        // New sequence step or append existing step
        if (key && key.length) {
          sequenceStep[key.trim()] = value.trim()
        }
      }
    }
    if (Object.keys(sequenceStep).includes('Presence')) {
      // Sequence step complete
      result.push(...explodeSequenceStep(sequenceStep))
      sequenceStep = {}
    }
  }
  return result
}

export function parseGenericCsv(cols, rows) {
  // Filter out rows where sample name is empty or None
  const validRows = rows.filter((row) => row[cols[0].field] && row[cols[0].field].trim() !== '')

  // Map over the filtered non-empty rows
  return validRows.map((row) => {
    // Determine if filter_id should be generated
    const checkTypesToGenerateFilterId = !['INSTRUMENT_BACKGROUND', 'ONLINE'].includes(
      row[cols[1].field],
    )

    const newSampleItem = {
      sample_item_name: row[cols[0].field],
      sample_item_type: row[cols[1].field] ? row[cols[1].field].trim() : 'UNKNOWN',
      // Generate filter_id only if the type is not "INSTRUMENT_BACKGROUND" or "ONLINE", for "INSTRUMENT_BACKGROUND" or "ONLINE" set filter_id to null
      filter_id: checkTypesToGenerateFilterId ? row[cols[2].field] || genId(6, false) : null,
      sample_item_attributes: {},
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
