<script setup>
import { ref, reactive, computed, watch, onMounted, onUnmounted } from 'vue'

import Button from 'primevue/button'
import Select from 'primevue/select'
import DatePicker from 'primevue/datepicker'
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'
import IconField from 'primevue/iconfield'
import InputIcon from 'primevue/inputicon'
import InputText from 'primevue/inputtext'
import FloatLabel from 'primevue/floatlabel'
import ContextMenu from 'primevue/contextmenu'

import { UppyContextProvider } from '@uppy/vue'
import '@uppy/core/css/style.min.css'
import Dashboard from '@uppy/dashboard'
import '@uppy/dashboard/css/style.min.css'
import DropTarget from '@uppy/drop-target'
import '@uppy/drop-target/css/style.min.css'

import {
  DialogSampleOp,
  DialogBatchImport,
  DialogFileUpload,
  DialogIonizationOp
} from '@/lib/dialogs'
import { InstrumentSelector } from '@/lib/toolbars'

import { api } from '@/api'
import { useApp } from '@/stores'

const app = useApp()
const uppy = app.uppy.get()

onMounted(() => {
  uppy
    .use(DropTarget, { target: '#uppy-drop-target' })
    .on('file-added', (file) => {
      const dashboard = uppy.getPlugin('Dashboard')
      if (dashboard) {
        dashboard.openModal()
      }
    })
    .use(Dashboard, {
      trigger: '#uppy-upload-trigger',
      inline: false,
      height: 600,
      showProgressDetails: true,
      theme: app.ui.darkmode.active ? 'dark' : 'light',
      closeModalOnClickOutside: true,
      closeAfterFinish: true,
      showProgressDetails: true,
      proudlyDisplayPoweredByUppy: false,
      note: 'Supported file types: .h5 (TOF), .raw (Orbi)'
    })
})

onUnmounted(() => {
  uppy.removePlugin(uppy.getPlugin('Dashboard'))
  uppy.removePlugin(uppy.getPlugin('DropTarget'))
})

const props = defineProps({
  active: {
    type: Boolean
  }
})

const dialog = reactive({
  sample: null,
  batchImport: false,
  mechanism: null
})

const contextMenuRef = ref(null)
const contextMenuItems = ref([
  {
    label: 'Download',
    icon: 'pi pi-download',
    command: () => {
      api.http.post(
        `/file/download`,
        {
          sample_file_ids: app.data.acquisition.selected.map(({ sample_file_id }) => sample_file_id)
        },
        {
          use: 'process',
          type: 'download_sample_files'
        }
      )
    }
  },
  {
    label: 'Delete',
    icon: 'pi pi-trash',
    command: () => {
      const sample_file_ids = app.data.acquisition.selected.map(
        ({ sample_file_id }) => sample_file_id
      )
      if (sample_file_ids.length > 0) {
        api.http.post(
          `/sample/files/delete`,
          { sample_file_ids },
          {
            use: 'delete',
            type: 'delete_sample_files'
          }
        )
      }
    }
  }
])
const contextMenuRow = ref(null)

const search = ref('')
const polarityDropdown = ref('')

const acquisitions = computed(
  () =>
    app.data.acquisition.list?.filter(
      ({ filename, polarity }) =>
        filename.toLowerCase().includes(search.value.toLowerCase()) &&
        (polarityDropdown.value === '' ||
          polarityDropdown.value === '+-' ||
          polarity === polarityDropdown.value ||
          polarity === '+-')
    ) ?? []
)
watch(
  acquisitions,
  () => {
    app.data.acquisition.selected = []
  },
  { deep: true }
)

const clearFilters = () => {
  app.data.acquisition.resetFilters()
  search.value = ''
  polarityDropdown.value = ''
}

// Check if files with both "+" and "-" polarities are selected
const hasBothPolarities = computed(() => {
  const hasPositive = app.data.acquisition.selected.some(({ polarity }) => polarity === '+')
  const hasNegative = app.data.acquisition.selected.some(({ polarity }) => polarity === '-')
  return hasPositive && hasNegative
})

// We consider "+-" as a mixed polarity type
const onlyMixedPolaritySelected = computed(() => {
  const allMixed = app.data.acquisition.selected.every(({ polarity }) => polarity === '+-')
  const moreThanOneSelected = app.data.acquisition.selected.length > 1
  const polarityNotSpecified = ['', '+-'].includes(polarityDropdown.value)
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
  const positive = app.data.acquisition.selected.every(({ polarity }) =>
    ['+', '+-'].includes(polarity)
  )
  const negative = app.data.acquisition.selected.every(({ polarity }) =>
    ['-', '+-'].includes(polarity)
  )
  if (positive) {
    return '+'
  } else if (negative) {
    return '-'
  } else {
    return null
  }
})
</script>

<template>
  <div>
    <menu class="acquisition-menu">
      <div class="row">
        <Button
          v-tooltip.top="'Edit ionizations'"
          label="Edit ionizations"
          class="hiddenlabel"
          icon="pi pi-sliders-h"
          text
          size="small"
          @click="
            () => {
              dialog.mechanism = true
            }
          "
        />
        <InstrumentSelector />
      </div>
      <Select
        inputId="time"
        v-model="app.data.acquisition.time.mode"
        :options="['Last 24 hours', 'Last 7 days', 'Last 30 days', 'Last 90 days']"
        style="flex-direction: row-reverse"
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
        <IconField class="full">
          <InputIcon>
            <i class="pi pi-search" />
          </InputIcon>
          <InputText v-model="search" placeholder="Search filenames" style="width: 100%" />
        </IconField>
      </FloatLabel>
      <Button
        icon="pi pi-filter-slash"
        @click="clearFilters"
        text
        severity="secondary"
        v-tooltip.left="'Clear filters and selection'"
      />
    </menu>
  </div>
  <div>
    <UppyContextProvider :uppy="uppy">
      <div id="uppy-drop-target">
        <DataTable
          v-if="acquisitions?.length"
          v-model:selection="app.data.acquisition.selected"
          v-model:contextMenuSelection="contextMenuRow"
          :value="acquisitions"
          :totalRecords="acquisitions.length"
          scrollable
          scrollHeight="calc(100vh - 320px)"
          sortField="datetime"
          :sortOrder="-1"
          size="small"
          selectionMode="multiple"
          dataKey="filename"
          :metaKeySelection="true"
          @rowContextmenu="
            (event) => {
              contextMenuRow = event.data
              event.originalEvent.preventDefault()
              if (
                !app.data.acquisition.selected.some(
                  ({ sample_file_id }) => sample_file_id === contextMenuRow.sample_file_id
                )
              ) {
                app.data.acquisition.selected = [contextMenuRow]
              }
              contextMenuRef?.show(event.originalEvent)
            }
          "
          :virtualScrollerOptions="{ itemSize: 28 }"
        >
          <Column header="Filename" field="filename" sortable />
          <Column header="Polarity" field="polarity" sortable />
          <Column header="Datetime" field="datetime" sortable />
          <template #footer>
            <div
              style="
                display: flex;
                justify-content: space-between;
                align-items: center;
                padding: 0.5rem;
              "
            >
              <strong v-if="app.data.acquisition.multiselected" style="font-style: italic">
                {{ app.data.acquisition.selected.length }} files selected
              </strong>
              <div v-else style="min-width: 11ch" />

              <div class="info-text">
                <span v-if="!app.data.batch.focused">
                  <span class="pi pi-info-circle" />
                  Select a batch to process the files.
                </span>
                <span v-else-if="hasBothPolarities">
                  <span class="pi pi-info-circle" />
                  Cannot process files with both "+" and "-" polarities selected.
                </span>
                <span v-else-if="onlyMixedPolaritySelected">
                  <span class="pi pi-info-circle" />
                  Only mixed polarity files selected. Please choose a polarity from the dropdown.
                </span>
              </div>
            </div>
          </template>
        </DataTable>
        <div v-else class="center" style="min-height: 150px">
          <i class="info-line"> <span class="pi pi-inbox" /><span>No acquisitions found</span> </i>
        </div>
        <i class="info-line">
          <span class="pi pi-file-arrow-up" /><span>Drag sample files here to upload them</span>
        </i>
        <menu class="bottom-menu">
          <Button id="uppy-upload-trigger" label="Upload" icon="pi pi-file-arrow-up" @click="" />
          <Button
            label="Process selected"
            icon="pi pi-file-plus"
            :disabled="
              app.data.acquisition.selected?.length == 0 ||
              !app.data.batch.focused ||
              hasBothPolarities ||
              onlyMixedPolaritySelected
            "
            :tooltip="
              !app.data.batch.focused || app.data.acquisition.selected.length === 0
                ? 'Select acquisitions and a batch in order to process sample files'
                : ''
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
      </div>
    </UppyContextProvider>

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
    <DialogFileUpload
      :files="app.uppy.invalidFiles"
      @upload="
        $event.map((file) => {
          try {
            uppy.addFile(file)
          } catch (error) {
            uppy.info(error, 'error')
          }
        })
      "
    />
    <DialogIonizationOp v-model:visible="dialog.mechanism" />
    <ContextMenu :model="contextMenuItems" ref="contextMenuRef" />
  </div>
</template>

<style scoped>
.acquisition-menu {
  gap: 1rem;
  align-items: baseline;
  height: fit-content;
  width: 100%;
  margin-bottom: 1rem;
}

.bottom-menu {
  gap: 1rem;
  align-items: baseline;
  height: fit-content;
  width: 100%;
  margin-bottom: 1rem;
  justify-content: flex-end;
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
