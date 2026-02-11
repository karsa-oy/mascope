<script setup>
import { computed, ref } from 'vue'

import { useWindowSize } from '@vueuse/core'

import DataTable from 'primevue/datatable'
import Column from 'primevue/column'
import Button from 'primevue/button'
import IconField from 'primevue/iconfield'
import InputIcon from 'primevue/inputicon'
import InputText from 'primevue/inputtext'

import { FilterMatchMode } from '@primevue/core/api'

import { BaseTabbedPanel, BaseCopyableField, BaseStatusIcon } from '@/lib/base'
import { useApp } from '@/stores'

import { useBatchContextMenu, useBatchStatus } from './stores'

const app = useApp()
const contextMenu = useBatchContextMenu()
const batchStatusStore = useBatchStatus()

const { height } = useWindowSize()
const padding = 100
const tableHeight = computed(() => ((height.value - padding) * app.ui.split.top) / 100 - 50)

const filters = ref({
  global: { value: null, matchMode: FilterMatchMode.CONTAINS }
})
</script>

<template v-if="app.data.batch.list">
  <BaseTabbedPanel
    label="Batches"
    icon="pi pi-tags"
    :contextMenu="contextMenu"
    :pt="
      app.ui.help.right(`
        <h1>Sample Browser: Batches</h1>

        <p>Shows all batches in the currently selected workspace 
        (${app.data.workspace.focused.workspace_name}).
        </p>

        <p>Click on a batch to open it and see the samples within.</p>

        <p>Right click on a batch to perform actions.</p>
      `)
    "
  >
    <template #menu>
      <div class="row">
        <IconField>
          <InputIcon>
            <i class="pi pi-search" />
          </InputIcon>
          <InputText v-model="filters['global'].value" type="text" placeholder="Search batches" />
        </IconField>
        <Button
          v-tooltip.top="'Create batch'"
          label="Create batch"
          class="hiddenlabel"
          icon="pi pi-plus"
          text
          size="small"
          @click="
            () => {
              contextMenu.dialog.op = 'create'
            }
          "
        />
      </div>
    </template>
    <DataTable
      :value="app.data.batch.list"
      dataKey="sample_batch_id"
      selectionMode="single"
      :metaKeySelection="false"
      v-model:selection="app.data.batch.focused"
      v-model:contextMenuSelection="contextMenu.selection"
      contextMenu
      @rowContextmenu="
        async (event) => {
          event.originalEvent.stopPropagation() // don't trigger handler in <Panel> (see above)
          event.originalEvent.preventDefault() // don't open default context menu
          await contextMenu.onClick(event)
        }
      "
      resizableColumns
      sortField="sample_batch_name"
      :sortOrder="-1"
      v-model:filters="filters"
      size="small"
      scrollable
      :scrollHeight="`${tableHeight}px`"
      :virtualScrollerOptions="{ itemSize: 35.74 }"
    >
      <!-- batch columns -->
      <Column header="Batch" field="sample_batch_name" sortable>
        <template #body="{ data }">
          <div class="row" style="justify-content: flex-start">
            <!-- Batch status icons -->
            <div style="width: 20px; display: flex; justify-content: center; align-items: center">
              <BaseStatusIcon
                :status="data.status"
                :config="batchStatusStore.config"
                :onAction="() => app.data.batch.rematch({ sample_batch_id: data.sample_batch_id })"
              />
            </div>
            <BaseCopyableField
              :field="data.sample_batch_name"
              v-tooltip="{ value: `${data.sample_batch_description}`, showDelay: 1000 }"
            />
          </div>
        </template>
      </Column>
    </DataTable>
  </BaseTabbedPanel>
</template>
