<script setup>
import { ref, reactive, computed } from 'vue'

import { dialog } from '@/main'

import BaseSpreadsheetInput from '@/components/base/BaseSpreadsheetInput.vue'

import { parseAutosamplerCsv, parseGenericCsv, genId } from '@/lib/util'

import { useBatchStore, useModalStore, useSampleStore, useNotificationStore } from '@/stores'

const batchStore = useBatchStore()
const modalStore = useModalStore()
const sampleStore = useSampleStore()
const notificationStore = useNotificationStore()

const csvCols = ref([])
const csvRows = ref([])
const parsedRows = ref([])
const sampleItemsToCreate = ref([]) // Array of objects containing sample_item data
// Pagination properties for sampleItemsToCreate
const samplesCurrentPage = ref(1)
const samplesPerPage = ref(12)
const activeTab = ref('input') // This will hold the value of the active tab
const importType = ref(null) // property for import type
const columnsValidation = ref(false) // the check theat pasted columns are valid
const sampleItemsValidation = ref(false) // the check theat pasted sample items fields are valid
// To store the details of validation failures
const failedValidations = reactive({
  messages: [],
  sampleFailures: [],
  columnsFailures: [],
  info: []
})
const showFilterIdInput = ref(false) // Controls visibility of filter ID input
const selectedFilterId = ref('') // Stores the selected filter ID

const modalTitle = computed(() => {
  const batchName = batchStore.active?.sample_batch_name ?? 'selected'
  // Define the modal title based on the importType
  switch (importType.value) {
    case 'autosampler':
      return `Import samples from the autosampler report to "${batchName}" batch`
    case 'general':
      return `Import samples from the spreedsheet input to "${batchName}" batch`
    default:
      return `Paste samples data to import to "${batchName}" batch`
  }
})
const sampleItemsToCreateLabel = computed(() =>
  importType.value == 'autosampler'
    ? `Please check carefully the details of the samples parsed from the autosampler report:`
    : `Please check carefully the details of the samples parsed from the spreedsheet input:`
)
// Data Input Tab
const batchFilterIds = computed(() => {
  return batchStore.active
    ? [null, ...new Set(batchStore.sampleItems.map((item) => item.filter_id))]
    : []
})
// Sample Items Tab
const tableColumns = computed(() => {
  if (sampleItemsToCreate.value.length === 0) {
    return []
  }

  const mainColumns = [
    { field: 'sample_item_name', label: 'Sample Name' },
    { field: 'filename', label: 'Filename' },
    { field: 'sample_item_type', label: 'Sample Type' },
    { field: 'filter_id', label: 'Filter ID' }
  ]

  // Find all unique attribute keys from sample_item_attributes
  const attributeKeys = new Set()
  sampleItemsToCreate.value.forEach((item) => {
    Object.keys(item.sample_item_attributes).forEach((key) => {
      attributeKeys.add(key)
    })
  })

  // Create columns for each attribute key
  const attributeColumns = Array.from(attributeKeys).map((key) => ({
    field: `sample_item_attributes.${key}`,
    label: key.replace(/_/g, ' ').replace(/\b\w/g, (l) => l.toUpperCase())
  }))

  return [...mainColumns, ...attributeColumns]
})

const paginatedSampleItemsToCreate = computed(() => {
  const start = (samplesCurrentPage.value - 1) * samplesPerPage.value
  const end = start + samplesPerPage.value
  return sampleItemsToCreate.value.slice(start, end)
})

function deactivateModalResetData() {
  modalStore.deactivate()
  resetData()
}

function generateFilterId() {
  selectedFilterId.value = genId(6, false)
}

function processButtonClick() {
  dialog.confirm({
    message: `Are you sure you want to import ${
      sampleItemsToCreate.value.length
    } samples into the batch '${batchStore.active?.sample_batch_name || ''}'?`,
    confirmText: 'Import',
    type: 'is-primary',
    hasIcon: true,
    icon: 'file-import',
    onConfirm: async () => {
      processSamples()
      deactivateModalResetData()
    }
  })
}

function resetData() {
  csvCols.value = []
  csvRows.value = []
  parsedRows.value = []
  sampleItemsToCreate.value = []
  selectedFilterId.value = ''
  importType.value = null
  showFilterIdInput.value = false
  activeTab.value = 'input'
  sampleItemsValidation.value = false
  columnsValidation.value = false
  notificationStore.closeGeneralNotification()
}

// Data processing

// csv loading columns
async function processCsvCols(cols) {
  resetData()
  if (!cols.length) return
  csvCols.value = []
  determineImportType(cols)
  validateColumns(cols)
  if (!columnsValidation.value) return
  csvCols.value = cols
}
// csv loading rows
async function processCsvRows(rows) {
  if (!rows.length) return
  csvRows.value = []
  if (!columnsValidation.value) return
  csvRows.value = rows
  parseCsv()
  if (!parsedRows.value) return
  if (importType.value === 'autosampler') {
    showFilterIdInput.value = true
  } else {
    preprocessSamples()
  }
}

function preprocessSamples() {
  prepareSampleItemsToCreate()
  activeTab.value = 'samples'
  samplesCurrentPage.value = 1
  validateImportedSampleItems()
}

function processSamples() {
  if (!sampleItemsValidation.value) return
  const data = {
    batch: batchStore.active,
    sample_items: sampleItemsToCreate.value
  }
  batchStore.importSamplesToBatch(data)
}

function determineImportType(cols) {
  // List of keys that can identify the autosampler report
  const autosamplerKeys = ['ht3000a_autorun_report', 'software', 'sample_list', 'autosampler']

  // Check if the field of any of the first few columns matches the autosampler keys
  const isAutosamplerReport = cols.some((col) => autosamplerKeys.includes(col.field.toLowerCase()))

  importType.value = isAutosamplerReport ? 'autosampler' : 'general'
}

function parseCsv() {
  if (importType.value === 'autosampler') {
    parsedRows.value = parseAutosamplerCsv(csvRows.value)
  } else if (importType.value === 'general') {
    parsedRows.value = parseGenericCsv(csvCols.value, csvRows.value)
  }
}

function prepareSampleItemsToCreate() {
  if (importType.value === 'autosampler') {
    let items = []
    for (let [i, row] of Object.entries(parsedRows)) {
      let newSampleItem = {
        filename: modalStore.state.sampleBatchImportProps.sampleFilesSelected[i]?.filename ?? null,
        sample_batch_id: batchStore.active.sample_batch_id,
        filter_id: selectedFilterId.value
      }
      let attributes = {}
      for (const key in row) {
        const attr = key.toLowerCase().replaceAll(/[\s-]/g, '_')
        if (attr.startsWith('sample_')) {
          // sample_name or sample_type
          const prop = attr.replace('sample', 'sample_item')
          newSampleItem[prop] = row[key]
        } else {
          attributes[attr] = row[key]
        }
      }

      newSampleItem.sample_item_attributes = attributes
      items.push(newSampleItem)
    }
    sampleItemsToCreate.value = items
    showFilterIdInput.value = false
    selectedFilterId.value = ''
  }
  // Process items for the general import
  if (importType.value === 'general') {
    // Transform the parsed rows into sample items with necessary properties
    sampleItemsToCreate.value = parsedRows.value.map((row, index) => {
      const newSampleItem = {
        sample_batch_id: batchStore.active.sample_batch_id,
        filename:
          modalStore.state.sampleBatchImportProps.sampleFilesSelected[index]?.filename ?? null,
        ...row // spread the already parsed row properties
      }
      return newSampleItem
    })
  }
}

//// Data validation ////
function validateColumns(cols) {
  // Clear previous validation failures
  failedValidations.messages = []
  failedValidations.sampleFailures = []
  failedValidations.columnsFailures = []
  failedValidations.info = []

  // skip column validation for autosampler report import
  if (importType.value === 'autosampler') {
    columnsValidation.value = true
    return
  }

  // Ensure all columns are labeled
  const unlabeledCols = cols.filter((col) => !col.label.trim())
  if (unlabeledCols.length > 0) {
    failedValidations.messages.push('All columns should be labeled.')
  }

  // Check for duplicated column names
  const columnNameCounts = {}
  cols.forEach((col) => {
    const label = col.label.trim()
    columnNameCounts[label] = (columnNameCounts[label] || 0) + 1
  })

  for (const label in columnNameCounts) {
    if (columnNameCounts[label] > 1) {
      failedValidations.columnsFailures.push(
        `Column label "${label}" is duplicated, each column should have the unique label`
      )
    }
  }

  // Check for empty column labels and specific naming conventions
  if (!cols[0] || cols[0].label.trim() === '') {
    failedValidations.columnsFailures.push(
      "The first column should be labeled to indicate it contains sample names (e.g., 'Sample Name', 'Name')."
    )
  }
  if (cols.length > 1 && (!cols[1] || cols[1].label.trim() === '')) {
    failedValidations.columnsFailures.push(
      "The second column should be labeled to indicate it contains sample types (e.g., 'Sample Type', 'Type')."
    )
  }
  if (cols.length > 2 && (!cols[2] || cols[2].label.trim() === '')) {
    failedValidations.columnsFailures.push(
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
    failedValidations.columnsFailures.push(
      `Column ${columnIndex} is unlabeled. Each column after the third must be labeled to indicate the name of the sample item attribute it contains.`
    )
  } else if (unlabeledAttributeColsIndices.length > 1) {
    const formattedIndices = unlabeledAttributeColsIndices.join(', ')
    failedValidations.columnsFailures.push(
      `Columns ${formattedIndices} should be labeled to indicate the name of the sample item attribute it contains.`
    )
  }

  // Show warning notification if there are any failed validations
  if (failedValidations.messages.length > 0 || failedValidations.columnsFailures.length > 0) {
    notificationStore.showWarningNotification({
      notification: 'validationErrors',
      data: failedValidations
    })
    columnsValidation.value = false // Column validation failed
  } else {
    columnsValidation.value = true // Column validation passed
  }
}

function validateImportedSampleItems() {
  // TODO_configuration possible collection types
  const FILTER_ID_REGEX = /^[0-9A-Z]{6}$/ // The regex pattern for filter ID validation

  if (!sampleItemsToCreate.value.length > 0) return
  // Clear previous validation failures
  failedValidations.messages = []
  failedValidations.sampleFailures = []
  failedValidations.columnsFailures = []
  failedValidations.info = []

  // Check for mismatch in the number of samples and files
  if (
    sampleItemsToCreate.value.length !==
    modalStore.state.sampleBatchImportProps.sampleFilesSelected.length
  ) {
    failedValidations.messages.push(
      `The number of pasted samples (${sampleItemsToCreate.value.length}) doesn't line up with the total number of selected files (${modalStore.state.sampleBatchImportProps.sampleFilesSelected.length}).
          Please ensure each pasted sample corresponds to a selected file.`
    )
  }

  // Iterate over each sample item to validate data
  for (const item of sampleItemsToCreate.value) {
    let itemFailures = [] // Store validation failures for the current item

    // Validate sample type
    if (!sampleStore.sampleTypes.includes(item.sample_item_type)) {
      itemFailures.push(
        `Sample type '${item.sample_item_type}' isn't recognized, please use one of the accepted types.`
      )

      // Add recommendation info if not already present
      const allowedTypesInfo = `Sample Types: please use one of the following: ${sampleStore.sampleTypes.join(
        ', '
      )}. You can leave this field empty, sample type will be set to UNKNOWN. `
      if (!failedValidations.info.includes(allowedTypesInfo)) {
        failedValidations.info.push(allowedTypesInfo)
      }
    }

    // Validate filter ID presence based on sample type
    if (['INSTRUMENT_BACKGROUND', 'ONLINE'].includes(item.sample_item_type) && item.filter_id) {
      itemFailures.push(
        `Filter ID should not be provided for sample type '${item.sample_item_type}'.`
      )
    } else if (
      !['INSTRUMENT_BACKGROUND', 'ONLINE'].includes(item.sample_item_type) &&
      !item.filter_id
    ) {
      itemFailures.push(`Filter ID must be provided for sample type '${item.sample_item_type}'.`)
    }

    // Validate filter ID format if present
    if (item.filter_id && !FILTER_ID_REGEX.test(item.filter_id)) {
      itemFailures.push(`The filter ID '${item.filter_id}' is incorrectly formatted.`)

      // Add recommendation info if not already present
      const allowedFilterIdInfo = `Filter ID: ensure it is exactly 6 characters long and only contains uppercase letters and numbers.
          You can leave this field empty, filter ID will be generated automatically.`
      if (!failedValidations.info.includes(allowedFilterIdInfo)) {
        failedValidations.info.push(allowedFilterIdInfo)
      }
    }

    // If there are failures, add them to the failedValidations array with the sample name
    if (itemFailures.length > 0) {
      failedValidations.sampleFailures.push({
        sampleName: item.sample_item_name,
        failures: itemFailures
      })
    }
  }

  // Show warning notification if there are any failed validations
  if (failedValidations.messages.length > 0 || failedValidations.sampleFailures.length > 0) {
    notificationStore.showWarningNotification({
      notification: 'validationErrors',
      data: failedValidations
    })
    return (sampleItemsValidation.value = false)
  }

  return (sampleItemsValidation.value = true)
}
</script>

<template>
  <section>
    <b-modal
      v-model="modalStore.state.sampleBatchImportActive"
      trap-focus
      :can-cancel="true"
      aria-role="dialog"
      aria-modal
      @close="deactivateModalResetData"
    >
      <div class="modal-card" style="height: 95vh; width: auto">
        <header class="modal-card-head">
          <h2 class="subtitle">{{ modalTitle }}</h2>
        </header>
        <section class="modal-card-body" style="min-height: 250px">
          <b-tabs v-model="activeTab" type="is-boxed" position="is-centered" expanded>
            <!-- Spreadsheet Input Tab -->
            <b-tab-item value="input" label="Data Input">
              <base-spreadsheet-input
                label="CSV"
                :cols="csvCols"
                :colsFromHeader="true"
                @colsPasted="processCsvCols"
                @rowsPasted="processCsvRows"
              />
              <!-- Filter ID input and dropdown -->
              <template v-if="showFilterIdInput">
                <b-field label="Please select the Filter ID">
                  <div style="display: flex; justify-content: space-between; align-items: center">
                    <div style="display: flex; align-items: center">
                      <b-button
                        type="is-primary"
                        icon-left="plus"
                        @click="generateFilterId"
                        style="margin-right: 10px"
                      >
                      </b-button>
                      <b-input v-model="selectedFilterId" disabled expanded></b-input>
                      <b-dropdown aria-role="list" v-model="selectedFilterId" expanded>
                        <template #trigger>
                          <b-button
                            :label="selectedFilterId || 'Select Filter ID'"
                            icon-right="menu-down"
                          />
                        </template>
                        <template v-for="filterId in batchFilterIds" :key="filterId">
                          <b-dropdown-item aria-role="listitem" :value="filterId">
                            {{ filterId }}
                          </b-dropdown-item>
                        </template>
                      </b-dropdown>
                    </div>
                    <b-button
                      type="is-primary"
                      @click="preprocessSamples"
                      :disabled="!selectedFilterId"
                    >
                      Continue
                    </b-button>
                  </div>
                </b-field>
              </template>
            </b-tab-item>

            <!-- Parsed Sample Items Tab -->
            <b-tab-item
              value="samples"
              label="Sample Items"
              :disabled="sampleItemsToCreate.length == 0"
            >
              <b-field :label="sampleItemsToCreateLabel" v-if="sampleItemsToCreate.length > 0">
                <div class="table-with-pagination">
                  <div class="table-container">
                    <b-table
                      v-if="sampleItemsToCreate.length > 0"
                      :data="paginatedSampleItemsToCreate"
                      :columns="tableColumns"
                    ></b-table>
                  </div>
                  <div class="pagination-container">
                    <b-pagination
                      :total="sampleItemsToCreate.length"
                      v-model:current="samplesCurrentPage"
                      :per-page="samplesPerPage"
                      size="is-small"
                    ></b-pagination>
                  </div>
                </div>
              </b-field>
            </b-tab-item>
          </b-tabs>
        </section>
        <footer class="modal-card-foot">
          <b-button type="is-dark" icon-left="close" expanded @click="deactivateModalResetData">
            Cancel
          </b-button>
          <b-button
            expanded
            type="is-primary"
            :disabled="!sampleItemsValidation"
            @click="processButtonClick"
          >
            Process ({{ sampleItemsToCreate.length }})
          </b-button>
        </footer>
      </div>
    </b-modal>
  </section>
</template>
