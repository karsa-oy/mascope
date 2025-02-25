<script setup>
import { ref, computed, watch, onMounted } from 'vue'

import Button from 'primevue/button'
import Popover from 'primevue/popover'
import Listbox from 'primevue/listbox'
import SelectButton from 'primevue/selectbutton'

import { beautifySnakeCase } from '@/lib/utils'
import { useApp } from '@/stores'

import { useCustomizerPopover } from './stores'

const app = useApp()

const customizer = useCustomizerPopover()

const popoverRef = ref()
onMounted(() => {
  customizer.popover = popoverRef.value
})

const tab = ref('All')

const defaultConfig = {
  columns: [
    { field: 'sample_item_name', kind: 'standard', label: 'Item', type: 'string' },
    { field: 'index', kind: 'standard', label: '#', type: 'string' },
    { field: 'filter_id', kind: 'standard', label: 'Filter', type: 'string' }
  ],
  sortField: 'index',
  sortOrder: 1
}

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

const storageKey = computed(() => `sample-browser-batch[${app.data.batch.focused.sample_batch_id}]`)
// write
watch(
  () => customizer.config,
  (state) => {
    localStorage.setItem(storageKey.value, JSON.stringify(state))
  },
  { deep: true }
)
// read
watch(
  () => app.data.batch.focused,
  (batch) => {
    if (batch) {
      const storedConfig = localStorage.getItem(storageKey.value)
      customizer.config = storedConfig ? JSON.parse(storedConfig) : defaultConfig
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
        customizer.show(event)
      }
    "
  />
  <Popover ref="popoverRef" contentStyle="height: fit-content;">
    <div class="row" style="margin-bottom: 0.5rem">
      <SelectButton v-model="tab" :options="['All', 'Selected']" :allowEmpty="false" />
      <Button
        label="Reset"
        icon="pi pi-replay"
        severity="secondary"
        iconPos="right"
        text
        @click="selectedColumns = defaultConfig.columns"
        v-tooltip.right="'Reset columns'"
      />
    </div>
    <Listbox
      v-model="customizer.config.columns"
      :options="
        availableColumns.filter(({ field }) =>
          tab == 'Selected' ? selectedColumns.map(({ field }) => field).includes(field) : true
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
