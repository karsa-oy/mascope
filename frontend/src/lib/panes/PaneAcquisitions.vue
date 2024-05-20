<script setup>
import { reactive, computed, watch, watchEffect } from 'vue'

import Button from 'primevue/button'
import Select from 'primevue/select'
import DatePicker from 'primevue/datepicker'
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'

import { DialogSampleItemOp, DialogSampleBatchImport } from '@/lib/dialogs'

import { useAppStore, useBatchStore, useInstrumentStore } from '@/stores'

const appStore = useAppStore()
const batchStore = useBatchStore()
const instrumentStore = useInstrumentStore()

const props = defineProps({
  active: {
    type: Boolean
  }
})

const dialog = reactive({
  sampleItem: null,
  batchImport: false
})

const selected = reactive({
  files: []
})

watchEffect(() => {
  if (instrumentStore.pending.filename && appStore.mode.measuring && props.active) {
    dialog.sampleItem = 'create_pending'
  }
})
watch(
  computed(() => instrumentStore.time),
  () => {
    selected.files = []
  },
  { deep: true }
)
</script>

<template>
  <menu>
    <Select
      props.inputId="time"
      v-model="instrumentStore.time.mode"
      :options="['Last 24 hours', 'Last 7 days', 'Last 30 days', 'Last 90 days']"
      style="flex-direction: row-reverse"
      :disabled="appStore.mode.measuring"
    />
    <DatePicker
      v-model="instrumentStore.time.range"
      selectionMode="range"
      inputId="range"
      showTime
      showIcon
      :class="instrumentStore.time.mode == 'range' ? '' : 'inactive'"
    />
    <menu>
      <Button
        label="Process"
        icon="pi pi-file-import"
        :disabled="
          selected.files?.length == 0 || !batchStore.active || !instrumentStore.acquisitions?.length
        "
        @click="
          () => {
            if (selected.files?.length == 1) {
              dialog.sampleItem = 'create'
            } else if (selected.files?.length > 1) {
              dialog.batchImport = true
            }
          }
        "
      />
    </menu>
  </menu>
  <DataTable
    v-if="instrumentStore.acquisitions?.length"
    v-model:selection="selected.files"
    :value="instrumentStore.acquisitions"
    :totalRecords="instrumentStore.acquisitions.length"
    scrollable
    scrollHeight="calc(100vh - 200px)"
    sortField="datetime"
    :sortOrder="-1"
    :rows="12"
    paginator
    size="small"
  >
    <Column selectionMode="multiple" headerStyle="width: 3rem" />
    <Column header="Filename" field="filename" sortable />
    <Column header="Datetime" field="datetime" sortable />
  </DataTable>
  <DialogSampleItemOp v-model:action="dialog.sampleItem" :item="selected.files[0]" />
  <DialogSampleBatchImport v-model:visible="dialog.batchImport" :files="selected.files" />
</template>

<style scoped>
menu {
  display: flex;
  flex-flow: row nowrap;
  gap: 0.5rem;
  justify-content: space-between;
  align-items: center;
  padding: 0;
}

menu :deep(*) {
  font-size: 12px;
}

:deep(#latest.p-inputtext) {
  width: 40px;
}
:deep(#range.p-inputtext) {
  width: 280px;
}

.inactive {
  opacity: 0.5;
}
</style>
