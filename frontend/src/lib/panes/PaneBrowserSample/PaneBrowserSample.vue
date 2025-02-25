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

import { useBatchContext } from './stores'

const app = useApp()

const context = useBatchContext()

const contextMenuRef = ref()
onMounted(() => {
  context.menu = contextMenuRef.value
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
        context.onClick(event)
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
            context.dialog.op = 'create'
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
        v-model:contextMenuSelection="context.selection"
        contextMenu
        @rowContextmenu="
          async (event) => {
            event.originalEvent.stopPropagation() // don't trigger handler in <Panel> (see above)
            event.originalEvent.preventDefault() // don't open default context menu
            await context.onClick(event)
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
            <SampleTableCustomizer v-if="data.sample_batch_id in batch.expanded" />
          </template>
        </Column>
        <!-- sample table expansion -->
        <template #expansion="{ data }">
          <SampleTable :batch="data" />
        </template>
      </DataTable>
    </div>
  </Panel>
  <!-- modals etc -->
  <ContextMenu ref="contextMenuRef" :model="context.entries" @hide="context.clear" />
  <DialogBatchOp v-model:action="context.dialog.op" :batch="context.row" />
  <DialogCalibration v-model:visible="context.dialog.calibration" :context="context.row" />
</template>
