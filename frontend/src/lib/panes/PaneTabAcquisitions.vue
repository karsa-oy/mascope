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
import FileUpload from 'primevue/fileupload'
import FloatLabel from 'primevue/floatlabel'

import { runtime } from '@/lib/runtime'
import { DialogSampleOp, DialogBatchImport, DialogFileUpload } from '@/lib/dialogs'

import { useApp } from '@/stores'

// TODO_configuration Default sample file upload params
const FILE_UPLOAD_EXTENSIONS = ['.h5', '.raw']

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

watch(
  () => app.data.instrument.focused,
  () => {
    selected.files = []
  }
)

const search = ref('')

const acquisitions = computed(
  () =>
    app.data.acquisition.list?.filter(({ filename }) =>
      filename.toLowerCase().includes(search.value.toLowerCase())
    ) ?? []
)

const uploadedFiles = ref([])

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
  <FileUpload
    name="samplefile[]"
    :accept="FILE_UPLOAD_EXTENSIONS.join(',')"
    :url="`${runtime.api_path}/api/sample/files/upload`"
    @select="(event) => (uploadedFiles = event.files)"
    customUpload
    multiple
    auto
  >
    <template #header="{ chooseCallback }">
      <menu class="acquisition-menu">
        <Select
          inputId="time"
          v-model="app.data.acquisition.time.mode"
          :options="['Last 24 hours', 'Last 7 days', 'Last 30 days', 'Last 90 days']"
          style="flex-direction: row-reverse"
          :disabled="app.data.acquisition.mode"
          placeholder="Custom range"
        />
        <FloatLabel>
          <label>Min. Datetime</label>
          <DatePicker
            v-model="app.data.acquisition.time.range.min"
            inputId="min-datetime"
            dateFormat="yy/mm/dd"
            showTime
            showIcon
            :class="'full ' + (app.data.acquisition.time.mode == 'range' ? '' : 'inactive')"
          />
        </FloatLabel>
        <FloatLabel>
          <label>Max. Datetime</label>
          <DatePicker
            v-model="app.data.acquisition.time.range.max"
            inputId="max-datetime"
            dateFormat="yy/mm/dd"
            showTime
            showIcon
            :class="'full ' + (app.data.acquisition.time.mode == 'range' ? '' : 'inactive')"
          />
        </FloatLabel>
        <div style="flex-grow: 1; flex-shrink: 1" />
        <FloatLabel style="flex-grow: 1; max-width: 250px">
          <label>Search</label>
          <IconField class="full">
            <InputIcon>
              <i class="pi pi-search" />
            </InputIcon>
            <InputText v-model="search" placeholder="Search" style="width: 100%" />
          </IconField>
        </FloatLabel>
        <Button label="Upload" icon="pi pi-file-arrow-up" @click="chooseCallback" />
        <Button
          label="Process"
          icon="pi pi-file-plus"
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
    </template>
    <template #empty>
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
        <i class="info-line"> <span class="pi pi-inbox" /><span>No acquisitions found</span> </i>
      </div>
      <DialogSampleOp v-model:action="dialog.sample" :item="selected.files[0]" />
      <DialogBatchImport v-model:visible="dialog.batchImport" :files="selected.files" />
      <DialogFileUpload :files="uploadedFiles" />
      <i class="info-line">
        <span class="pi pi-file-arrow-up" /><span>Drag sample files here to upload them</span>
      </i>
    </template>
  </FileUpload>
</template>

<style scoped>
.acquisition-menu {
  gap: 1rem;
  align-items: baseline;
  height: fit-content;
  width: 100%;
}

menu {
  display: flex;
  flex-flow: row nowrap;
  gap: 0.5rem;
  justify-content: space-between;
  align-items: center;
  padding: 0;
  margin: 0;
}

menu > :deep(*) {
  margin-bottom: 0;
}

menu :deep(*) {
  font-size: 12px;
}

menu :deep(.full) {
  width: 100%;
}

.inactive {
  opacity: 0.5;
}

.info-line {
  width: 100%;
  display: flex;
  flex-flow: row;
  justify-content: center;
  align-items: center;
  opacity: 0.5;
  gap: 0.5rem;
  margin: 0.5rem;
}
</style>
