<script setup>
import { ref, reactive, computed, watch, watchEffect } from 'vue'

import Button from 'primevue/button'
import Select from 'primevue/select'
import DatePicker from 'primevue/datepicker'
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'
import IconField from 'primevue/iconfield'
import InputIcon from 'primevue/inputicon'
import InputText from 'primevue/inputtext'

import { DialogSampleOp, DialogBatchImport } from '@/lib/dialogs'

import { useApp } from '@/stores'

const app = useApp()

const props = defineProps({
  active: {
    type: Boolean
  }
})

const dialog = reactive({
  sample: null,
  batchImport: false
})

const selected = reactive({
  files: []
})

const search = ref('')

const acquisitions = computed(
  () =>
    app.data.acquisition.list?.filter(({ filename }) =>
      filename.toLowerCase().includes(search.value.toLowerCase())
    ) ?? []
)

watchEffect(() => {
  if (app.data.acquisition.pending.filename && app.data.acquisition.mode && props.active) {
    dialog.sample = 'create_pending'
  }
})
watch(
  computed(() => app.data.acquisition.time),
  () => {
    selected.files = []
  },
  { deep: true }
)
</script>

<template>
  <div id="acquisitions">
    <menu style="gap: 2rem">
      <Select
        props.inputId="time"
        v-model="app.data.acquisition.time.mode"
        :options="['Last 24 hours', 'Last 7 days', 'Last 30 days', 'Last 90 days']"
        style="flex-direction: row-reverse"
        :disabled="app.data.acquisition.mode"
      />
      <DatePicker
        v-model="app.data.acquisition.time.range"
        selectionMode="range"
        inputId="range"
        showTime
        showIcon
        :class="app.data.acquisition.time.mode == 'range' ? '' : 'inactive'"
        style="flex-grow: 1"
      />
      <IconField style="flex-grow: 1">
        <InputIcon>
          <i class="pi pi-search" />
        </InputIcon>
        <InputText v-model="search" placeholder="Search" style="width: 100%" />
      </IconField>
      <menu>
        <Button
          label="Process"
          icon="pi pi-file-import"
          :disabled="
            selected.files?.length == 0 ||
            !app.data.batch.focused ||
            !app.data.acquisition.list.length
          "
          @click="
            () => {
              if (selected.files?.length == 1) {
                dialog.sample = 'create'
              } else if (selected.files?.length > 1) {
                dialog.batchImport = true
              }
            }
          "
        />
      </menu>
    </menu>
    <DataTable
      v-if="acquisitions?.length"
      v-model:selection="selected.files"
      :value="acquisitions"
      :totalRecords="acquisitions.length"
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
      <template #paginatorstart>
        <strong v-if="selected.files.length" style="font-style: italic">
          {{ selected.files.length }} files selected
        </strong>
        <div v-else style="min-width: 11ch" />
      </template>
      <template #paginatorend> <div style="min-width: 12ch" /> </template>
    </DataTable>
    <div v-else class="center" style="min-height: 150px">
      <i>No acquisitions found</i>
    </div>
    <DialogSampleOp v-model:action="dialog.sample" :item="selected.files[0]" />
    <DialogBatchImport v-model:visible="dialog.batchImport" :files="selected.files" />
  </div>
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
