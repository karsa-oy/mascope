<script setup>
import { ref, computed, watch } from 'vue'

import Button from 'primevue/button'
import Popover from 'primevue/popover'
import Listbox from 'primevue/listbox'
import SelectButton from 'primevue/selectbutton'

import { beautifySnakeCase } from '@/lib/utils'
import { useApp } from '@/stores'

const app = useApp()

const popoverRef = ref()
const popoverTab = ref('All')

const selectedColumns = defineModel('columns')

const emit = defineEmits(['popover'])

const defaultColumns = [
  { field: 'sample_item_name', kind: 'standard', label: 'Item', type: 'string' },
  { field: 'index', kind: 'standard', label: '#', type: 'string' },
  { field: 'filter_id', kind: 'standard', label: 'Filter', type: 'string' }
]

const availableColumns = computed(() => {
  const standard = [
    ...new Set(
      app.data.sample.list
        ?.map((item) => Object.keys(item ?? {}))
        .flat()
        .filter((field) => field !== 'sample_item_attributes')
    )
  ].map((field) => ({ field, kind: 'standard' }))
  const custom = [
    ...new Set(
      app.data.sample.list?.map((item) => Object.keys(item?.sample_item_attributes ?? {})).flat()
    )
  ].map((field) => ({ field, kind: 'custom' }))
  return [...standard, { field: 'time', kind: 'custom', label: 'Time' }, ...custom]
    .map(({ field, kind }) => ({
      field,
      kind,
      label: createLabel(field),
      type: kind == 'custom' ? 'string' : inferType(field)
    }))
    .filter(({ type }) => type !== 'object')
})

// local storage persistence

const storageKey = computed(
  () => `mascope-sample-columns-${app.data.batch.focused.sample_batch_id}`
)
// write
watch(selectedColumns, (cols) => {
  localStorage.setItem(storageKey.value, JSON.stringify(cols))
})
// read
watch(
  () => app.data.batch.focused,
  (batch) => {
    if (batch) {
      const storedColumns = localStorage.getItem(storageKey.value)
      selectedColumns.value = storedColumns ? JSON.parse(storedColumns) : defaultColumns
    }
  },
  { immediate: true }
)

// utils

function inferType(field) {
  const withField = app.data.sample.list.filter((item) => field in item)
  const types = [
    ...new Set(withField.map((item) => (item[field] ? typeof item[field] : 'null')))
  ].filter((type) => type !== 'null')
  return types.length == 1 ? types[0] : 'unknown'
}

function createLabel(field) {
  const custom = {
    index: '#',
    sample_item_name: 'Item',
    filter_id: 'Filter'
  }
  if (field in custom) {
    return custom[field]
  } else {
    return beautifySnakeCase(field)
  }
}
</script>

<template v-if="app.data.batch.list">
  <Button
    v-tooltip.top="'Edit batch fields'"
    icon="pi pi-ellipsis-h"
    severity="secondary"
    text
    size="small"
    @click="
      (event) => {
        event.stopPropagation()
        emit('popover', popoverRef)
        popoverRef.show(event)
      }
    "
  />
  <Popover ref="popoverRef" contentStyle="height: fit-content;">
    <div class="row" style="margin-bottom: 0.5rem">
      <SelectButton v-model="popoverTab" :options="['All', 'Selected']" :allowEmpty="false" />
      <Button
        label="Reset"
        icon="pi pi-replay"
        severity="secondary"
        iconPos="right"
        text
        @click="selectedColumns = defaultColumns"
        v-tooltip.right="'Reset columns'"
      />
    </div>
    <Listbox
      v-model="selectedColumns"
      :options="
        availableColumns.filter(({ field }) =>
          popoverTab == 'Selected'
            ? selectedColumns.map(({ field }) => field).includes(field)
            : true
        )
      "
      multiple
      optionLabel="label"
      filter
      dataKey="field"
      style="height: 230px"
    />
  </Popover>
</template>

<style scoped>
:deep(.p-listbox-list-container) {
  height: 180px;
}
</style>
