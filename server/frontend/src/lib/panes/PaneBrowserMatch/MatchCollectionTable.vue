<script setup>
import { ref, reactive, inject } from 'vue'

import Button from 'primevue/button'
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'
import ContextMenu from 'primevue/contextmenu'

import { BaseTabbedPanel, BaseMatchTag, BaseCopyableField } from '@/lib/base'
import { DialogTargetCollectionOp } from '@/lib/dialogs'
import { num } from '@/lib/formatters'

import { useApp } from '@/stores'

const app = useApp()

const context = reactive({
  record: null,
  menuItems: [
    {
      label: 'Edit collection',
      icon: 'pi pi-pen-to-square',
      command: () => {
        dialog.collection = 'update'
      }
    },
    {
      label: 'Edit batches',
      icon: 'pi pi-pen-to-square',
      command: () => {
        dialog.collection = 'update_batches'
      }
    },
    {
      label: 'Delete collection',
      icon: 'pi pi-trash',
      command: () => {
        dialog.collection = 'delete'
      }
    }
  ]
})
const contextMenuRef = ref()

const dialog = reactive({
  collection: null
})

const tableHeight = inject('match-table-height')

const icon = {
  TARGETS: 'pi ph ph-target',
  DIAGNOSTICS: 'pi ph ph-stethoscope',
  CALIBRANTS: 'pi ph ph-scales'
}
</script>

<template v-if="collections">
  <BaseTabbedPanel
    label="Target Collections"
    icon="pi ph ph-crosshair"
    :loading="app.data.match.collection.pending"
    :pt="
      app.ui.help.right(`
        <h1>Target Browser</h1>

        <p>Shows the targets and matches associated
        with the currently selected batch, and provides
        features for managing them.</p>

        <p>Right click on collections and compounds to
        perform actions.</p>
      `)
    "
  >
    <template #menu>
      <Button
        v-tooltip.top="'Create collection'"
        label="Create collection"
        class="hiddenlabel"
        icon="pi pi-plus"
        text
        size="small"
        @click="
          () => {
            dialog.collection = 'create'
          }
        "
      />
    </template>
    <DataTable
      :value="app.data.match.collection.list"
      dataKey="target_collection_id"
      v-model:selection="app.data.match.collection.focused"
      selectionMode="single"
      :metaKeySelection="false"
      contextMenu
      v-model:contextMenuSelection="context.record"
      @rowContextmenu="
        async (event) => {
          context.record = event.data
          // Load detailed data for context menu operations without focusing
          await app.data.target.collection.loadDetailed(event.data.target_collection_id)
          contextMenuRef.show(event.originalEvent)
        }
      "
      resizableColumns
      size="small"
      scrollable
      :scrollHeight="`${tableHeight}px`"
      :virtualScrollerOptions="{ itemSize: 35.74 }"
      sortField="match_score"
      :sortOrder="-1"
    >
      <Column sortable sortField="match.match_score" class="match-column">
        <template #header>
          <span class="pi pi-verified" />
        </template>
        <template #body="{ data }">
          <BaseMatchTag
            :match-score="data.match?.match_score"
            :match-category="data.match?.match_category"
            :alarming="data.match?.alarming"
            :tooltip="
              data.match?.sample_peak_intensity_sum
                ? `Peak intensity: ${num.peakIntensity.format(data.match.sample_peak_intensity_sum)} (cps)`
                : 'No peak intensity data'
            "
          />
        </template>
      </Column>
      <Column header="Collection" field="target_collection_name" sortable>
        <template #body="{ data }">
          <div :id="data.target_collection_id" class="row" style="justify-content: flex-start">
            <span
              :class="icon[data.target_collection_type]"
              v-tooltip.top="data.target_collection_type.toLowerCase()"
              style="margin-right: 0.5rem"
            />
            <BaseCopyableField :field="data.target_collection_name" />
          </div>
        </template>
      </Column>
    </DataTable>
    <ContextMenu ref="contextMenuRef" :model="context.menuItems" />
  </BaseTabbedPanel>
  <DialogTargetCollectionOp v-model:action="dialog.collection" :collection="context.record" />
</template>

<style scoped>
.active-filter {
  visibility: visible !important;
  color: var(--p-button-text-info-color);
  opacity: 0.7;
}
</style>
