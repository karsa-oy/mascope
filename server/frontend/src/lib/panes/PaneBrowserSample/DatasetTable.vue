<script setup>
import { ref, computed, watch } from 'vue'

import { useWindowSize } from '@vueuse/core'

import DataTable from 'primevue/datatable'
import Column from 'primevue/column'
import Button from 'primevue/button'
import IconField from 'primevue/iconfield'
import InputIcon from 'primevue/inputicon'
import InputText from 'primevue/inputtext'
import ContextMenu from 'primevue/contextmenu'

import { BaseTabbedPanel, BaseCopyableField } from '@/lib/base'
import { DialogDatasetOp } from '@/lib/dialogs'
import { useApp } from '@/stores'

import { useDatasetTableConfig } from './stores'

const app = useApp()
const datasetTable = useDatasetTableConfig()

const dialog = ref()
const selectedDataset = ref(null)
const datasetContextMenu = ref()

// Track filtered count for display
const filteredCount = ref(0)

// Handle filter event
const onFilter = (event) => {
  filteredCount.value = (event.filteredValue ?? []).length
}

// Initialize when dataset list changes
watch(
  () => app.data.dataset.list,
  (newList) => {
    filteredCount.value = (newList ?? []).length
  },
  { immediate: true }
)

const { height } = useWindowSize()
const padding = 100
const tableHeight = computed(() => ((height.value - padding) * app.ui.split.top) / 100 - 50)
</script>

<template v-if="app.data.dataset.list">
  <BaseTabbedPanel
    :label="
      datasetTable.config.filters?.global?.value
        ? `Datasets (${filteredCount}/${app.data.dataset.list?.length})`
        : `Datasets (${app.data.dataset.list?.length})`
    "
    icon="pi ph ph-folders"
    :pt="
      app.ui.help.right(`
        <h1>Sample Browser: Datasets</h1>

        <p>Shows all datasets in the currently selected workspace
        (${app.data.workspace.focused?.workspace_name}).
        </p>

        <p>Click on a dataset to open it and see the batches within.</p>

        <p>Right click on a dataset to edit or delete it.</p>
      `)
    "
  >
    <template #menu>
      <div class="row">
        <IconField>
          <InputIcon>
            <i class="pi pi-search" />
          </InputIcon>
          <InputText
            v-model="datasetTable.config.filters['global'].value"
            type="text"
            placeholder="Search datasets"
          />
        </IconField>
        <Button
          v-tooltip.top="'Create dataset'"
          label="Create dataset"
          class="hiddenlabel"
          icon="pi pi-plus"
          text
          size="small"
          @click="
            () => {
              dialog = 'create'
            }
          "
        />
      </div>
    </template>
    <DataTable
      :value="app.data.dataset.list"
      dataKey="dataset_id"
      selectionMode="single"
      :metaKeySelection="false"
      v-model:selection="app.data.dataset.focused"
      v-model:contextMenuSelection="selectedDataset"
      contextMenu
      @rowContextmenu="
        (event) => {
          event.originalEvent.stopPropagation()
          event.originalEvent.preventDefault()
          selectedDataset = event.data
          datasetContextMenu.toggle(event.originalEvent)
        }
      "
      resizableColumns
      :sortField="datasetTable.config.sortField"
      :sortOrder="datasetTable.config.sortOrder"
      v-model:filters="datasetTable.config.filters"
      @filter="onFilter"
      @sort="
        ({ sortField, sortOrder }) => {
          datasetTable.config.sortField = sortField
          datasetTable.config.sortOrder = sortOrder
        }
      "
      size="small"
      scrollable
      :scrollHeight="`${tableHeight}px`"
      :virtualScrollerOptions="{ itemSize: 35.74 }"
    >
      <Column header="Dataset" field="dataset_name" sortable>
        <template #body="{ data }">
          <div class="row" style="justify-content: flex-start">
            <svg
              xmlns="http://www.w3.org/2000/svg"
              width="16"
              height="16"
              fill="currentColor"
              viewBox="0 0 256 256"
              style="opacity: 0.4"
            >
              <path
                d="M216,72H130.67L102.93,51.2a16.12,16.12,0,0,0-9.6-3.2H40A16,16,0,0,0,24,64V200a16,16,0,0,0,16,16H216.89A15.13,15.13,0,0,0,232,200.89V88A16,16,0,0,0,216,72Zm0,128H40V64H93.33L123.2,86.4A8,8,0,0,0,128,88h88Z"
                v-if="data.dataset_type === 'ANALYSIS'"
              ></path>
              <path
                v-else
                d="M224,208H203.94A88.05,88.05,0,0,0,144,64.37V32a16,16,0,0,0-16-16H80A16,16,0,0,0,64,32V136a16,16,0,0,0,16,16h48a16,16,0,0,0,16-16V80.46A72,72,0,0,1,181.25,208H32a8,8,0,0,0,0,16H224a8,8,0,0,0,0-16Zm-96-72H80V32h48V136ZM72,184a8,8,0,0,1,0-16h64a8,8,0,0,1,0,16Z"
              ></path>
            </svg>
            <BaseCopyableField
              :field="data.dataset_name"
              v-tooltip="{ value: data.dataset_description, showDelay: 1000 }"
            />
          </div>
        </template>
      </Column>
    </DataTable>
  </BaseTabbedPanel>
  <ContextMenu
    ref="datasetContextMenu"
    appendTo="self"
    :model="[
      {
        label: 'Edit dataset',
        icon: 'pi pi-pen-to-square',
        command: () => {
          dialog = 'edit'
        }
      },
      {
        label: 'Delete dataset',
        icon: 'pi pi-trash',
        command: () => {
          dialog = 'delete'
        }
      }
    ]"
  />
  <DialogDatasetOp v-model:action="dialog" :dataset="selectedDataset" />
</template>
