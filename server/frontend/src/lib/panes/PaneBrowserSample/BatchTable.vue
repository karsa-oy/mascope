<script setup>
import { computed } from 'vue'

import { useWindowSize } from '@vueuse/core'

import DataTable from 'primevue/datatable'
import Column from 'primevue/column'
import Button from 'primevue/button'
import ProgressSpinner from 'primevue/progressspinner'

import { BaseTabbedPanel, BaseCopyableField } from '@/lib/base'
import { useApp } from '@/stores'

import { useBatchContextMenu } from './stores'

const app = useApp()
const contextMenu = useBatchContextMenu()

const { height } = useWindowSize()
const padding = 100
const tableHeight = computed(() => ((height.value - padding) * app.ui.split.top) / 100 - 50)
</script>

<template v-if="app.data.batch.list">
  <BaseTabbedPanel
    label="Batches"
    icon="pi pi-tags"
    :contextMenu="contextMenu"
    :pt="
      app.ui.help.right(`
        <h1>Sample Browser</h1>

        <p>Shows the samples in your workspace,
        providing features to organize them into
        batches.</p>

        <p>Right click batches and samples to
        perform actions.</p>
      `)
    "
  >
    <template #menu>
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
      sortField="sample_batch_utc_created"
      :sortOrder="-1"
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
              <Button
                v-if="data.status === 'rematch'"
                v-tooltip.right="
                  'Sample batch has been modified, matches may be out of date. Click to refresh this batch matches'
                "
                icon="ph ph-arrows-clockwise"
                text
                rounded
                size="small"
                severity="secondary"
                @click.stop="app.data.batch.rematch({ sample_batch_id: data.sample_batch_id })"
              />
              <Button
                v-else-if="data.status === 'ready'"
                v-tooltip.right="'Sample batch matches are up to date'"
                icon="ph ph-check-circle"
                text
                rounded
                size="small"
                severity="primary"
                disabled
              />
              <div
                v-else-if="data.status === 'processing'"
                v-tooltip.right="'Sample batch is processing, computing matches'"
                style="display: flex; align-items: center; justify-content: center"
              >
                <ProgressSpinner style="width: 16px; height: 16px" strokeWidth="3" />
              </div>
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
