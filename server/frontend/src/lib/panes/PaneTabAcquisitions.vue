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
const polarityFilter = ref('') // Default polarity filter

const acquisitions = computed(() => {
  return (
    app.data.acquisition.list?.filter(({ filename, polarity }) => {
      const matchesSearch = filename.toLowerCase().includes(search.value.toLowerCase())
      const matchesPolarity =
        polarityFilter.value === '' || polarity === polarityFilter.value || polarity === '+-'
      return matchesSearch && matchesPolarity
    }) ?? []
  )
})

const uploadedFiles = ref([])

// Check if files with both "+" and "-" polarities are selected
const hasMixedPolarities = computed(() => {
  const selectedPolarities = new Set(
    app.data.acquisition.selected?.map((file) => file.polarity)
  )
  return selectedPolarities.has('+') && selectedPolarities.has('-')
})

const polarityNotSpecified = computed(() => {
  const selectedPolarities = new Set(
    app.data.acquisition.selected?.map((file) => file.polarity)
  )
  return (
    !selectedPolarities.has('+') &&
    !selectedPolarities.has('-') &&
    polarityFilter.value === '' &&
    selectedPolarities.has('+-') &&
    app.data.acquisition.selected?.length > 1
  )
})

// Watch for polarity changes and clear selected acquisitions
watch(polarityFilter, () => {
  app.data.acquisition.selected = [] // Clear selected acquisitions
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
        <!-- Polarity Dropdown -->
        <Select
          inputId="polarity"
          v-model="polarityFilter"
          :options="['', '+', '-']"
          style="max-width: 125px"
          placeholder="Polarity"
        />
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
            !app.data.acquisition.list.length ||
            hasMixedPolarities ||
            polarityNotSpecified
          "
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
        <template #paginatorend> <div style="min-width: 12ch" /> </template>
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
        @submit="app.data.acquisition.unfocus()"
      />
      <DialogFileUpload :files="uploadedFiles" />
      <i class="info-line">
        <span class="pi pi-file-arrow-up" /><span>Drag sample files here to upload them</span>
      </i>
      <div class="warning-plate-container">
        <Message
          v-if="!app.data.batch.focused"
          class="warning-plate"
          severity="warn"
          icon="pi pi-exclamation-triangle"
        >
          <span>Select the batch to process the files.</span>
        </Message>
        <Message
          v-if="hasMixedPolarities"
          class="warning-plate"
          severity="warn"
          icon="pi pi-exclamation-triangle"
        >
          <span>Cannot process files with both "+" and "-" polarities selected.</span>
        </Message>
        <Message
          v-if="polarityNotSpecified"
          class="warning-plate"
          severity="warn"
          icon="pi pi-exclamation-triangle"
        >
            <span>Files with mixed polarities are selected. Please specify a polarity.</span>
        </Message>
      </div>
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

.warning-plate {
  display: flex;
  align-items: center;
  justify-content: flex-start;
  max-width: fit-content;
  margin-bottom: 0.5rem;
}

.warning-plate-container {
  display: flex;
  align-items: flex-start;
  flex-flow: column;
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
