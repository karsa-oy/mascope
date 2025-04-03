<script setup>
import { ref, reactive, computed, watchEffect, onMounted } from 'vue'

import Panel from 'primevue/panel'
import Button from 'primevue/button'
import TabMenu from 'primevue/tabmenu'
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'
import ContextMenu from 'primevue/contextmenu'

import { BaseCopyableField } from '@/lib/base'
import { DialogBatchOp, DialogCalibration } from '@/lib/dialogs'
import { useApp } from '@/stores'

import SampleTable from './SampleTable.vue'
import SampleTableCustomizer from './SampleTableCustomizer.vue'

import { useBatchContextMenu } from './stores'

const app = useApp()

const contextMenu = useBatchContextMenu()

const contextMenuRef = ref()
onMounted(() => {
  contextMenu.ref = contextMenuRef.value
})

const batch = reactive({
  expanded: {}
})

// computed
const tree = computed(() => {
  return app.data.batch.list.map((batch) => ({
    ...batch,
    children:
      app.data.sample.list?.filter((sample) => sample.sample_batch_id == batch.sample_batch_id) ??
      []
  }))
})

watchEffect(() => {
  if (app.data.batch.focused) {
    batch.expanded = { [app.data.batch.focusedId]: true }
  } else {
    batch.expanded = {}
  }
})
</script>

<template v-if="app.data.batch.list">
  <Panel
    class="browser"
    style="border: none"
    @contextmenu.prevent.stop="
      (event) => {
        contextMenu.onClick(event)
      }
    "
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
    <template #header>
      <TabMenu :model="[{ label: 'Samples', icon: 'pi pi-tags' }]" />
    </template>
    <template #icons>
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
    <div class="scroller">
      <DataTable
        :value="tree"
        dataKey="sample_batch_id"
        selectionMode="single"
        :metaKeySelection="false"
        v-model:selection="app.data.batch.focused"
        v-model:expandedRows="batch.expanded"
        v-model:contextMenuSelection="contextMenu.selection"
        contextMenu
        @rowContextmenu="
          async (event) => {
            event.originalEvent.stopPropagation() // don't trigger handler in <Panel> (see above)
            event.originalEvent.preventDefault() // don't open default context menu
            await contextMenu.onClick(event)
          }
        "
        sortField="sample_batch_utc_created"
        :sortOrder="-1"
        size="small"
      >
        <!-- batch columns -->
        <Column header="Batch" field="sample_batch_name" sortable>
          <template #body="{ data }">
            <div
              class="row"
              style="justify-content: flex-start"
              v-help.right="
                `<h1>Batch</h1>

                <p>A group of samples. Right click to perform actions.</p>`
              "
            >
              <span
                :class="`pi pi-chevron-${data.sample_batch_id in batch.expanded ? 'down' : 'right'}`"
                style="font-size: smaller; margin-right: 0.5rem"
              />
              <BaseCopyableField
                :field="data.sample_batch_name"
                v-tooltip="{ value: `${data.sample_batch_description}`, showDelay: 1000 }"
              />
            </div>
          </template>
        </Column>
        <Column>
          <template #body="{ data }">
            <slot name="toolbar" v-if="data.sample_batch_id in batch.expanded"></slot>
          </template>
        </Column>
        <!-- sample table expansion -->
        <template #expansion="{ data }">
          <slot name="expansion" :batch="data"></slot>
        </template>
      </DataTable>
    </div>
  </Panel>
  <!-- modals etc -->
  <ContextMenu ref="contextMenuRef" :model="contextMenu.entries" @hide="contextMenu.clear" />
  <DialogBatchOp v-model:action="contextMenu.dialog.op" :batch="contextMenu.row" />
  <DialogCalibration v-model:visible="contextMenu.dialog.calibration" :context="contextMenu.row" />
</template>
