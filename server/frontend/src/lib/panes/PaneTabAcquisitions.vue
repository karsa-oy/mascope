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
import { Message } from 'primevue'

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

const search = ref('')
const polarityDropdown = ref('')

const acquisitions = computed(() => 
  app.data.acquisition.list?.filter(({ filename, polarity }) => 
    filename.toLowerCase().includes(search.value.toLowerCase()) &&
    (polarityDropdown.value === '' ||
      polarityDropdown.value === '+-' ||
      polarity === polarityDropdown.value ||
      polarity === '+-')
  ) ?? []
);

const uploadedFiles = ref([])

// Check if files with both "+" and "-" polarities are selected
const hasBothPolarities = computed(() => {
  const hasPositive = app.data.acquisition.selected.some(({ polarity }) => polarity === '+')
  const hasNegative = app.data.acquisition.selected.some(({ polarity }) => polarity === '-')
  return hasPositive && hasNegative
})

// We consider "+-" as a mixed polarity type
const onlyMixedPolaritySelected = computed(() => {
  const allMixed = app.data.acquisition.selected.every(({polarity}) => polarity === '+-')
  const moreThanOneSelected = app.data.acquisition.selected.length > 1
  const polarityNotSpecified = ['','+-'].includes(polarityDropdown.value)
  return allMixed && moreThanOneSelected && polarityNotSpecified
})

// Watch for polarity changes and clear selected acquisitions
watch(polarityDropdown, () => {
  app.data.acquisition.selected = [] // Clear selected acquisitions
})

const derivedPolarity = computed(() => {
  if (['+', '-'].includes(polarityDropdown.value)) {
    return polarityDropdown.value
  }
  const hasPositive = app.data.acquisition.selected.some(({ polarity }) => polarity === '+')
  const hasNegative = app.data.acquisition.selected.some(({ polarity }) => polarity === '-')
  const hasMixed = app.data.acquisition.selected.some(({ polarity }) => polarity === '+-')
  if (hasPositive && hasMixed) {
    return '+'
  }
  if (hasNegative && hasMixed) {
    return '-'
  }
  return null
})

watchEffect(() => {
  if (app.data.acquisition.pending.filename && app.data.acquisition.mode && props.active) {
    dialog.sample = 'create_pending'
  }
})
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
    :pt="{ root: { style: 'border: none; padding: 0' } }"
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
        <Select
          inputId="polarity"
          v-model="polarityDropdown"
          :options="['+-', '+', '-']"
          style="max-width: 125px"
          placeholder="Polarity"
        />
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
            app.data.acquisition.selected?.length == 0 ||
            !app.data.batch.focused ||
            hasBothPolarities ||
            onlyMixedPolaritySelected
          "
          :tooltip="!app.data.batch.focused || app.data.acquisition.selected.length === 0 
            ? 'Select acquisitions and a batch in order to process sample files' 
            : ''"
          @click="
            () => {
              if (app.data.acquisition.focused) {
                dialog.sample = 'create'
              } else if (app.data.acquisition.multiselected) {
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
        v-model:selection="app.data.acquisition.selected"
        :value="acquisitions"
        :totalRecords="acquisitions.length"
        scrollable
        scrollHeight="calc(100vh - 350px)"
        sortField="datetime"
        :sortOrder="-1"
        :rows="25"
        paginator
        size="small"
      >
        <Column selectionMode="multiple" headerStyle="width: 3rem" />
        <Column header="Filename" field="filename" sortable />
        <Column header="Polarity" field="polarity" sortable />
        <Column header="Datetime" field="datetime" sortable />
        <template #paginatorstart>
          <strong v-if="app.data.acquisition.multiselected" style="font-style: italic">
            {{ app.data.acquisition.selected.length }} files selected
          </strong>
          <div v-else style="min-width: 11ch" />
        </template>
        <template #paginatorend>
          <div class="info-text">
            <span v-if="!app.data.batch.focused">
              <span class="pi pi-info-circle"/>
              Select a batch to process the files.
            </span>
            <span v-else-if="hasBothPolarities">
              <span class="pi pi-info-circle"/>
              Cannot process files with both "+" and "-" polarities selected.
            </span>
            <span v-else-if="onlyMixedPolaritySelected">
              <span class="pi pi-info-circle"/>
              Only mixed polarity files selected. Please choose a polarity from the dropdown.
            </span>
          </div>
        </template>
      </DataTable>
      <div v-else class="center" style="min-height: 150px">
        <i class="info-line"> <span class="pi pi-inbox" /><span>No acquisitions found</span> </i>
      </div>
      <DialogSampleOp
        v-model:action="dialog.sample"
        :item="app.data.acquisition.focused"
        @submit="app.data.acquisition.unfocus()"
      />
      <DialogBatchImport
        v-model:visible="dialog.batchImport"
        :files="app.data.acquisition.selected"
        :polarity="derivedPolarity"
        @submit="app.data.acquisition.unfocus()"
      />
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

.info-text .pi {
  display: inline-flex;
  align-items: center;
  font-size: 1.2em;
  vertical-align: middle;
}

.info-text {
  font-style: italic;
}


</style>
