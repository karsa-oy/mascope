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
import Dialog from 'primevue/dialog'

import { runtime } from '@/lib/runtime'
import { DialogSampleOp, DialogBatchImport } from '@/lib/dialogs'

import { useApp } from '@/stores'

// TODO_configuration Default sample file upload params
const FILE_UPLOAD_EXTENSIONS = ['.h5', '.raw']
const FILE_UPLOAD_SIZE_LIMIT = 200 * 1024 * 1024 // 200 MB

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

const instrumentDialog = reactive({
  active: false,
  badFiles: [],
  goodFiles: [],
  instrument: null
})

// Validate file sizes before upload
function validateUploadFiles(files) {
  // size validation
  const oversizedFiles = files.filter((file) => file.size > FILE_UPLOAD_SIZE_LIMIT)
  if (oversizedFiles.length > 0) {
    const n = oversizedFiles.length
    const files = oversizedFiles.length > 1 ? 'files' : 'file'
    const exceed = oversizedFiles.length > 1 ? 'exceed' : 'exceeds'
    const max = FILE_UPLOAD_SIZE_LIMIT / (1024 * 1024)
    app.ui.notification.push({
      type: 'sample_file_upload',
      status: 'warning',
      message: `${n} ${files} ${exceed} the size limit of ${max} MB.`
    })
    return false
  }
  // instrument name validation
  const isMisnamed = ({name}) => !app.data.instrument.list
    // instrument names
    .map(({instrument}) => instrument).includes(
      // prefix
      name.split('_')[0]
    )
  const misnamedFiles = files
    .filter(isMisnamed)
  if (misnamedFiles.length > 0) {
    instrumentDialog.badFiles = misnamedFiles
    instrumentDialog.goodFiles = files
      .filter((f) => !isMisnamed(f))
    instrumentDialog.active = true
    return false
  }
  return true
}

// Handle file selection
function uploadFiles(event) {
  // Validate file sizes
  if (validateUploadFiles(event.files)) {
    // Proceed with upload if all files are valid
    app.data.sample.upload(event.files)
  }
}


const uploadFilesWithInstrument = () => {
  const renamedFiles = instrumentDialog.badFiles.map(
    (file) => {
      const newFilename = `${instrumentDialog.instrument}_${file.name}`
      return new File(
        [file],
        newFilename,
        {type: file.type}
      );
    }
  )
  instrumentDialog.active = false
  app.data.sample.upload([
    ...renamedFiles,
    ...instrumentDialog.goodFiles
  ])
}

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
    @select="uploadFiles"
    customUpload
    multiple
    auto
  >
    <template #header="{ chooseCallback }">
      <menu style="gap: 1rem; align-items: baseline; height: fit-content">
        <Select
          props.inputId="time"
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
        <FloatLabel>
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
      <Dialog :visible="instrumentDialog.active" modal header="Select instrument for files">
        <p>
          The prefix following file names is not an
          instrument in the database:
        </p>
        <ul>
          <li v-for="file in instrumentDialog.badFiles" :key="file.name">
            {{ file.name }}
          </li>
        </ul>
        <p>
          Please select an instrument to assign these files to:
        </p>
        <div class="center" style="width: 100%">
        <FloatLabel>
          <Select
            inputId="file-instrument"
            v-model="instrumentDialog.instrument"
            :options="app.data.instrument.list"
            dataKey="instrument"
            optionLabel="instrument"
            optionValue="instrument"
            style="min-width: 200px"
          />
          <label for="file-instrument"> Instrument </label>
        </FloatLabel>
        </div>
        <menu style="justify-content: flex-end">
            <Button
              label="Cancel"
              icon="pi pi-times"
              severity="secondary"
              @click="instrumentDialog.active = false"
            />
            <Button
              label="Save"
              icon="pi pi-save"
              :disabled="!instrumentDialog.instrument"
              @click="uploadFilesWithInstrument"
            />
        </menu>
      </Dialog>
      <i class="info-line">
        <span class="pi pi-file-arrow-up" /><span>Drag sample files here to upload them</span>
      </i>
    </template>
  </FileUpload>
</template>

<style scoped>
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
