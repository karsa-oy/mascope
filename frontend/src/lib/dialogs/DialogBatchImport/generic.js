import { useApp } from '@/stores'
import {
  sampleTypesFilterIdOptional,
  sampleTypesFilterIdRequired,
  sampleTypesFilterIdNotAllowed
} from '@/lib/constants'
import { strToSnakeCase, genId } from '@/lib/utils'

export const generic = {
  parse: (cols, rows) => {
    // Filter out rows where sample name is empty or None
    const validRows = rows.filter((row) => row[cols[0].field] && row[cols[0].field].trim() !== '')

    // Map over the filtered non-empty rows
    return validRows.map((row) => {
      // Parse the sample type field
      const parsed_sample_type = row[cols[1].field]
        .trim() // remove leading/trailing whitespace
        .replace(/\s\s+/g, ' ') // replace duplicate spaces with one space
        .replace(' ', '_') // replace spaces with underscores
        .toUpperCase() // capitalize

      // Set filter_id based on the sample type requirements
      let filter_id = null
      if (sampleTypesFilterIdRequired.includes(parsed_sample_type)) {
        filter_id = row[cols[2].field]?.toUpperCase() ?? genId(6, false)
      } else if (sampleTypesFilterIdNotAllowed.includes(parsed_sample_type)) {
        filter_id = null
      } else if (sampleTypesFilterIdOptional.includes(parsed_sample_type)) {
        filter_id = row[cols[2].field]?.toUpperCase() || null
      }

      const newSample = {
        sample_item_name: row[cols[0].field],
        sample_item_type: row[cols[1].field] ? parsed_sample_type : 'UNKNOWN',
        filter_id: filter_id,
        sample_item_attributes: {}
      }

      // Process the rest of the columns for sample_item_attributes
      cols.slice(3).forEach((col) => {
        const attrKey = strToSnakeCase(col.label.trim())
        // Ensure that if the attribute is empty, we set it to a default or empty string
        newSample.sample_item_attributes[attrKey] =
          col.field && row[col.field].trim() ? row[col.field].trim() : ''
      })
      return newSample
    })
  },
  preprocess: (acquisitions, parsed) => {
    const app = useApp()
    return parsed.map((parsed, index) => ({
      datetime: acquisitions[index]?.datetime ?? null,
      filename: acquisitions[index]?.filename ?? null,
      ...parsed,
      sample_batch_id: app.data.batch.focused.sample_batch_id
    }))
  }
}
