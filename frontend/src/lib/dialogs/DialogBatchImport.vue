<script setup>
import FloatLabel from 'primevue/floatlabel'
import Select from 'primevue/select'
import ScrollPanel from 'primevue/scrollpanel'
import Panel from 'primevue/panel'
import Button from 'primevue/button'
import Tabs from 'primevue/tabs'
import TabList from 'primevue/tablist'
import Tab from 'primevue/tab'
import TabPanels from 'primevue/tabpanels'
import TabPanel from 'primevue/tabpanel'
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'
import Message from 'primevue/message'
import Dialog from 'primevue/dialog'
import { useConfirm } from 'primevue/useconfirm'

import { ref, reactive, computed, watch } from 'vue'

import { BaseClipboardContext } from '@/lib/base'
import { fromSpreadsheet, parseAutosamplerCsv, parseGenericCsv } from '@/lib/table'
import { genId } from '@/lib/utils'
import { sampleTypes } from '@/lib/constants'

import { useApp } from '@/stores'

const confirm = useConfirm()

const app = useApp()

const visible = defineModel('visible')

const props = defineProps({
  files: {
    type: Object,
    required: true
  }
})

const tab = ref('data')

const imported = reactive({
  parsed: [],
  items: [],
  type: null,
  filterId: null
})
const generated = reactive({
  filterId: null
})
const filters = computed(() => {
  return app.data.batch.focused
    ? [
        null,
        ...(generated.filterId ? [generated.filterId] : []),
        ...new Set(app.data.sample.list.map(({ filter_id }) => filter_id).filter((f) => f))
      ]
    : generated
})

const validation = reactive({
  rows: {
    issues: [],
    passed: false
  },
  cols: {
    issues: [],
    passed: false
  }
})
const title = computed(() => {
  const name = app.data.batch.focused?.sample_batch_name ?? 'selected'
  return imported.type == 'autosampler'
    ? `Import autosampler sample data to "${name}" batch`
    : `Import spreadsheet sample data to "${name}" batch`
})

// Sample Items Tab
const columns = computed(() => {
  if (imported.items.length === 0) return []
  const core = [
    { field: 'sample_item_name', label: 'Sample Name' },
    { field: 'filename', label: 'Filename' },
    { field: 'sample_item_type', label: 'Sample Type' },
    { field: 'filter_id', label: 'Filter ID' }
  ]
  const attributes = [
    // find unique attributes
    ...new Set(imported.items.map((item) => Object.keys(item.sample_item_attributes)).flat())
  ].map((key) => ({
    field: `sample_item_attributes.${key}`,
    label: key.replace(/_/g, ' ').replace(/\b\w/g, (l) => l.toUpperCase())
  }))
  return [...core, ...attributes]
})

watch(visible, init)
function init(active) {
  if (!active) return
  tab.value = 'data'
  imported.parsed = []
  imported.items = []
  imported.filterId = ''
  imported.type = null
  validation.cols.passed = false
  validation.rows.passed = false
}

// processing
async function parse(text) {
  init()
  const { cols, rows } = fromSpreadsheet(text)
  if (!cols.length || !rows.length) return
  // columns
  const autosamplerKeys = ['ht3000a_autorun_report', 'software', 'sample_list', 'autosampler']
  imported.type = cols.some((col) => autosamplerKeys.includes(col.field))
    ? 'autosampler'
    : 'general'
  validateColumns(cols)
  if (!validation.cols.passed) return
  // rows
  if (imported.type === 'autosampler') {
    imported.parsed = parseAutosamplerCsv(rows)
  } else if (imported.type === 'general') {
    imported.parsed = parseGenericCsv(cols, rows)
  }
  if (imported.parsed) {
    preprocess()
  }
}

watch(
  computed(() => imported.filterId),
  preprocess
)
function preprocess() {
  // Sort acquisitions by datetime in descending order
  const acquisitions = [...props.files].sort((a, b) => b.datetime - a.datetime)
  if (imported.type === 'autosampler') {
    if (!imported.filterId) {
      imported.filterId = generated.filterId = genId(6, false)
    }
    imported.items = imported.parsed.map((parsed, i) => {
      const item = {
        filename: acquisitions[i]?.filename ?? null,
        sample_batch_id: app.data.batch.focused.sample_batch_id,
        filter_id: imported.filterId,
        sample_item_attributes: {}
      }
      Object.entries(parsed).forEach(([key, value]) => {
        const attr = key.toLowerCase().replaceAll(/[\s-]/g, '_')
        if (attr.startsWith('sample_')) {
          // some fields go into the base record
          const prop = `sample_item_${attr.slice(7)}`
          item[prop] = value
        } else {
          // others remain in `attributes`
          item.sample_item_attributes[attr] = value
        }
      })
      return item
    })
  }
  if (imported.type === 'general') {
    imported.items = imported.parsed.map((parsed, index) => ({
      ...parsed,
      sample_batch_id: app.data.batch.focused.sample_batch_id,
      filename: acquisitions[index]?.filename ?? null
    }))
  }
  validateRows()
}

// validation
function validateColumns(cols) {
  validation.cols.issues = []
  // skip column validation for autosampler report import
  if (imported.type === 'autosampler') {
    validation.cols.passed = true
    return
  }
  // Ensure all columns are labeled
  const unlabeledCols = cols.filter((col) => !col.label.trim())
  if (unlabeledCols.length > 0) {
    validation.cols.issues.push('All columns should be labeled.')
  }
  // Check for duplicated column names
  const columnNameCounts = {}
  cols.forEach((col) => {
    const label = col.label.trim()
    columnNameCounts[label] = (columnNameCounts[label] || 0) + 1
  })
  for (const label in columnNameCounts) {
    if (columnNameCounts[label] > 1) {
      validation.cols.issues.push(
        `Column label "${label}" is duplicated, each column should have the unique label`
      )
    }
  }
  // Check for empty column labels and specific naming conventions
  if (!cols[0] || cols[0].label.trim() === '') {
    validation.cols.issues.push(
      "The first column should be labeled to indicate it contains sample names (e.g., 'Sample Name', 'Name')."
    )
  }
  if (cols.length > 1 && (!cols[1] || cols[1].label.trim() === '')) {
    validation.cols.issues.push(
      "The second column should be labeled to indicate it contains sample types (e.g., 'Sample Type', 'Type')."
    )
  }
  if (cols.length > 2 && (!cols[2] || cols[2].label.trim() === '')) {
    validation.cols.issues.push(
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
    validation.cols.issues.push(
      `Column ${columnIndex} is unlabeled. Each column after the third must be labeled to indicate the name of the sample item attribute it contains.`
    )
  } else if (unlabeledAttributeColsIndices.length > 1) {
    const formattedIndices = unlabeledAttributeColsIndices.join(', ')
    validation.cols.issues.push(
      `Columns ${formattedIndices} should be labeled to indicate the name of the sample item attribute it contains.`
    )
  }

  // Show warning notification if there are any failed validations
  if (validation.cols.issues.length > 0) {
    tab.value = 'issues'
    validation.cols.passed = false
  } else {
    validation.cols.passed = true
  }
}

const friendlyType = (sample) => `'${sample.sample_item_type.replaceAll('_', ' ').toLowerCase()}'`
const friendlyTypes = sampleTypes
  .map((type) => `'${type.replaceAll('_', ' ').toLowerCase()}'`)
  .join(', ')

function validateRows() {
  validation.rows.issues = []
  let key = 0
  if (!imported.items.length > 0) return
  // Check for mismatch in the number of samples and files
  if (imported.items.length !== props.files.length) {
    validation.rows.issues.push({
      key,
      sample: null,
      failures: [
        `The number of pasted samples (${imported.items.length}) doesn't line up with the total number of selected files (${props.files.length}).
          Please ensure each pasted sample corresponds to a selected file.`
      ]
    })
  }
  // Iterate over each sample item to validate data
  for (const item of imported.items) {
    key++
    let failures = []
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
      if (!validation.rows.issues.includes(allowedTypes)) {
        validation.rows.issues.push(allowedTypes)
      }
    }
    // Validate filter ID presence based on sample type
    if (['INSTRUMENT_BACKGROUND', 'ONLINE'].includes(item.sample_item_type) && item.filter_id) {
      failures.push(`Filter ID should not be provided for sample type '${friendlyType(item)}'.`)
    } else if (
      !['INSTRUMENT_BACKGROUND', 'ONLINE'].includes(item.sample_item_type) &&
      !item.filter_id
    ) {
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
      if (!validation.rows.issues.includes(allowedFilterIdInfo)) {
        validation.rows.issues.push(allowedFilterIdInfo)
      }
    }
    // If there are failures, add them to the failedValidations array with the sample name
    if (failures.length > 0) {
      validation.rows.issues.push({
        key,
        sample: item.sample_item_name,
        failures
      })
    }
  }
  // Show warning notification if there are any failed validations
  if (validation.rows.issues.length > 0) {
    tab.value = 'issues'
    validation.rows.passed = false
  } else {
    validation.rows.passed = true
  }
}

watch(
  computed(() => validation.rows.passed && validation.cols.passed),
  autoswitchTab
)
function autoswitchTab(passed) {
  if (tab.value == 'issues' && passed) {
    // switch to data data
    tab.value = 'data'
  }
}
</script>

<template>
  <Dialog v-model:visible="visible" :header="title">
    <Tabs v-model:value="tab">
      <TabList>
        <Tab value="data">Data</Tab>
        <Tab
          value="issues"
          :disabled="validation.cols.issues.length == 0 && validation.rows.issues.length == 0"
        >
          Issues
        </Tab>
      </TabList>
      <TabPanels>
        <TabPanel value="data">
          <BaseClipboardContext
            info="Paste sample spreadsheet cells with 'name', 'type', 'filter id' columns, and (optionally) extra fields. Include headers and verify the row count matches your selection."
            :parse="parse"
            :persistMessage="imported.items.length == 0"
          >
            <p v-if="imported.type">
              Please check carefully the details of the samples parsed from the
              {{ imported.type == 'autosampler' ? 'autosample report' : 'spreedsheet input:' }}
            </p>
            <Panel v-if="imported.items.length > 0">
              <ScrollPanel style="height: 25vh; max-width: 80vw">
                <DataTable
                  :value="imported.items"
                  scrollable
                  scrollHeight="300px"
                  tableStyle="max-width: 70vw"
                >
                  <Column
                    v-for="col of columns"
                    :key="col.field"
                    :field="col.field"
                    :header="col.label"
                  />
                </DataTable>
              </ScrollPanel>
            </Panel>
            <i v-else style="position: absolute; top: 1rem">No spreadsheet data pasted</i>
          </BaseClipboardContext>
        </TabPanel>
        <TabPanel value="issues">
          <Panel>
            <ScrollPanel style="height: 300px; max-width: 80vw">
              <template v-if="validation.cols.issues.length > 0">
                <b>Column issues:</b>
                <Message
                  icon="pi pi-exclamation-circle"
                  severity="secondary"
                  v-for="msg in validation.cols.issues"
                  :key="msg"
                  :closable="false"
                >
                  {{ msg }}
                </Message>
              </template>
              <template v-if="validation.rows.issues.length > 0">
                <b>Row issues</b>
                <template v-for="issue in validation.rows.issues" :key="issue.key">
                  <p v-if="issue.sample">
                    Item <i>{{ issue.sample }}</i> (#{{ issue.key }}):
                  </p>
                  <Message
                    icon="pi pi-exclamation-circle"
                    v-for="failure in issue.failures"
                    severity="secondary"
                    :closable="false"
                    :key="failure"
                  >
                    {{ failure }}
                  </Message>
                </template>
              </template>
            </ScrollPanel>
          </Panel>
        </TabPanel>
      </TabPanels>
    </Tabs>
    <!-- Dialog Menu -->
    <menu style="justify-content: space-between">
      <div v-if="imported.type == 'general'" />
      <menu v-else>
        <FloatLabel>
          <Select inputId="item-filter-id" v-model="imported.filterId" :options="filters" />
          <label for="item-filter-id">Filter ID</label>
        </FloatLabel>
        <Button
          @click="imported.filterId = generated.filterId = genId(6, false)"
          icon="pi pi-sparkles"
        />
      </menu>
      <menu>
        <Button label="Cancel" severity="secondary" @click="visible = false" />
        <Button
          :label="`Process (${imported.items.length})`"
          :disabled="!validation.rows.passed"
          @click="
            () => {
              confirm.require({
                header: 'Import samples',
                message: `Are you sure you want to import ${imported.items.length} samples into the batch '${app.data.batch.focused?.sample_batch_name}'?`,
                rejectLabel: 'Cancel',
                acceptLabel: 'Import',
                accept: () => {
                  if (!validation.rows.passed) return
                  app.data.batch.importSamples({
                    batch: app.data.batch.focused,
                    sample_items: imported.items
                  })
                  visible = false
                }
              })
            }
          "
        />
      </menu>
    </menu>
  </Dialog>
</template>

<style scoped>
.item-filter {
  padding: 0;
  margin: 0;
  gap: 0.5rem;
  display: flex;
  flex-flow: row nowrap;
  align-items: baseline;
}
.item-filter :deep(*) {
  margin: 0;
}

:deep(.p-select) {
  min-width: 200px;
}

:deep(.p-message) {
  max-width: 500px;
  margin: 0.5rem auto;
}
</style>
