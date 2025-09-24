import { ref } from 'vue'
import { reactiveComputed } from '@vueuse/core'

import {
  sampleTypes,
  sampleTypesFilterIdRequired,
  sampleTypesFilterIdNotAllowed
} from '@/lib/constants'

const friendlyType = (sample) => `'${sample.sample_item_type.replaceAll('_', ' ').toLowerCase()}'`
const friendlyTypes = sampleTypes
  .map((type) => `'${type.replaceAll('_', ' ').toLowerCase()}'`)
  .join(', ')

export function useValidation({ imported }) {
  const cols = useColsValidation({ imported })
  const rows = useRowsValidation({ imported })
  return reactiveComputed(() => ({
    cols,
    rows,
    passed: cols.passed && rows.passed,
    issues: cols.issues.length + rows.issues.length,
    reset: () => {
      cols.reset()
      rows.reset()
    }
  }))
}

export function useColsValidation({ imported }) {
  const passed = ref(false)
  const issues = ref([])

  const reset = () => {
    passed.value = false
    issues.value = []
  }

  const execute = ({ cols }) => {
    reset()
    // skip column validation for autosampler report import
    if (imported.type === 'autosampler') {
      passed.value = true
      return
    }
    // Ensure all columns are labeled
    const unlabeledCols = cols.filter((col) => !col.label.trim())
    if (unlabeledCols.length > 0) {
      issues.value.push('All columns should be labeled.')
    }
    // Check for duplicated column names
    const columnNameCounts = {}
    cols.forEach((col) => {
      const label = col.label.trim()
      columnNameCounts[label] = (columnNameCounts[label] || 0) + 1
    })
    for (const label in columnNameCounts) {
      if (columnNameCounts[label] > 1) {
        issues.value.push(
          `Column label "${label}" is duplicated, each column should have the unique label`
        )
      }
    }
    // Check for empty column labels and specific naming conventions
    if (!cols[0] || cols[0].label.trim() === '') {
      issues.value.push(
        "The first column should be labeled to indicate it contains sample names (e.g., 'Sample Name', 'Name')."
      )
    }
    if (cols.length > 1 && (!cols[1] || cols[1].label.trim() === '')) {
      issues.value.push(
        "The second column should be labeled to indicate it contains sample types (e.g., 'Sample Type', 'Type')."
      )
    }
    if (cols.length > 2 && (!cols[2] || cols[2].label.trim() === '')) {
      issues.value.push(
        "The third column should be labeled to indicate it contains filter IDs (e.g., 'Filter ID', 'Filter')."
      )
    }
    // Identify unlabeled sample item attribute columns and list their indices
    const unlabeledAttributeColsIndices = cols
      .slice(3)
      .map((col, index) => (!col.label.trim() ? index + 4 : null))
      .filter((index) => index !== null)

    if (unlabeledAttributeColsIndices.length === 1) {
      const columnIndex = unlabeledAttributeColsIndices[0]
      issues.value.push(
        `Column ${columnIndex} is unlabeled. Each column after the third must be labeled to indicate the name of the sample item attribute it contains.`
      )
    } else if (unlabeledAttributeColsIndices.length > 1) {
      const formattedIndices = unlabeledAttributeColsIndices.join(', ')
      issues.value.push(
        `Columns ${formattedIndices} should be labeled to indicate the name of the sample item attribute it contains.`
      )
    }

    // Show warning notification if there are any failed validations
    if (issues.value.length > 0) {
      passed.value = false
    } else {
      passed.value = true
    }
  }

  return reactiveComputed(() => ({
    passed,
    issues,
    reset,
    execute
  }))
}

export function useRowsValidation({ imported }) {
  const passed = ref(false)
  const issues = ref([])

  const reset = () => {
    passed.value = false
    issues.value = []
  }

  const execute = ({ files }) => {
    issues.value = []
    let key = 0
    if (!imported.items.length > 0) return
    // Check for mismatch in the number of samples and files
    if (imported.items.length !== files.length) {
      issues.value.push({
        key,
        sample: null,
        failures: [
          `The number of pasted samples (${imported.items.length}) doesn't line up with the total number of selected files (${files.length}).
          Please ensure each pasted sample corresponds to a selected file.`
        ]
      })
    }
    // Iterate over each sample item to validate data
    for (const item of imported.items) {
      key++
      let failures = []
      // Validate ionization mode token in filename
      if (!imported.availableIonizationModes.some((mode) => item.filename.includes(mode.token))) {
        failures.push(`Ionization mode token not found in filename '${item.filename}'.`)
      }
      // Validate sample type
      if (!sampleTypes.includes(item.sample_item_type)) {
        failures.push(
          `Sample type '${friendlyType(item)}' isn't recognized,` +
            `please use one of the accepted types: ${friendlyTypes}.`
        )
        // Add recommendation info if not already present
        const allowedTypes =
          `Please use one of the allowed sample types: ${friendlyTypes}.` +
          ` You can leave this field empty, sample type will be set to 'unknown'. `
        if (!issues.value.includes(allowedTypes)) {
          issues.value.push(allowedTypes)
        }
      }
      // Validate filter ID presence based on sample type
      if (sampleTypesFilterIdNotAllowed.includes(item.sample_item_type) && item.filter_id) {
        failures.push(`Filter ID should not be provided for sample type '${friendlyType(item)}'.`)
      } else if (sampleTypesFilterIdRequired.includes(item.sample_item_type) && !item.filter_id) {
        failures.push(`Filter ID must be provided for sample type '${friendlyType(item)}'.`)
      }
      // Validate filter ID format if present
      if (item.filter_id && !/^[0-9A-Z]{6}$/.test(item.filter_id)) {
        failures.push(
          `The filter ID '${item.filter_id}' is incorrectly formatted: ` +
            `filter ID must be consist of exactly 6 letters and/or numbers,` +
            ` e.g XYZ123, 420fyi, 1a2B3c, 123456, QWERTY.`
        )

        // Add recommendation info if not already present
        const allowedFilterIdInfo = `Filter ID: ensure it is exactly 6 characters long and only contains uppercase letters and numbers.
          You can leave this field empty, filter ID will be generated automatically.`
        if (!issues.value.includes(allowedFilterIdInfo)) {
          issues.value.push(allowedFilterIdInfo)
        }
      }
      // If there are failures, add them to the failedValidations array with the sample name
      if (failures.length > 0) {
        issues.value.push({
          key,
          sample: item.sample_item_name,
          failures
        })
      }
    }
    // Show warning notification if there are any failed validations
    if (issues.value.length > 0) {
      passed.value = false
    } else {
      passed.value = true
    }
  }

  return reactiveComputed(() => ({
    passed,
    issues,
    reset,
    execute
  }))
}
