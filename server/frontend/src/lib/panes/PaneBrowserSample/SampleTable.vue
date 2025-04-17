<script setup>
import { computed } from 'vue'

import DataTable from 'primevue/datatable'
import Column from 'primevue/column'
import ProgressSpinner from 'primevue/progressspinner'
import ContextMenu from 'primevue/contextmenu'
import { useConfirm } from 'primevue/useconfirm'

import { BaseMatchTag, BaseCopyableField } from '@/lib/base'
import { DialogSampleOp, DialogCalibration } from '@/lib/dialogs'
import { clone } from '@/lib/utils'
import { num } from '@/lib/formatters'
import { useApp } from '@/stores'

import { useSampleContextMenu, useCustomizerPopover } from './stores'

const confirm = useConfirm()
const app = useApp()

const customizer = useCustomizerPopover()
const contextMenu = useSampleContextMenu()

const props = defineProps({
  batch: {
    type: Object,
    required: true
  }
})

const samples = computed(() => props.batch?.children ?? [])

const formatter = new Intl.NumberFormat('en-US', {
  minimumFractionDigits: 2,
  maximumFractionDigits: 2
})
</script>

<template>
  <div
    v-if="!app.data.sample.loading"
    style="min-height: 2rem"
    v-help.right_start="
      `<h1>Samples</h1>
    
      <p>Sample items. Right click to perform actions.</p>`
    "
  >
    <DataTable
      v-if="samples.length > 0 && app.data.batch.focused"
      :value="samples"
      dataKey="sample_item_id"
      selectionMode="multiple"
      :metaKeySelection="true"
      v-model:selection="app.data.sample.selected"
      v-model:contextMenuSelection="contextMenu.selection"
      contextMenu
      @rowContextmenu="
        async (event) => {
          event.originalEvent.stopPropagation() // don't trigger batch context menu
          event.originalEvent.preventDefault() // don't open default context menu
          await contextMenu.onClick(event)
        }
      "
      reorderableColumns
      :sortField="customizer.config.sortField"
      :sortOrder="customizer.config.sortOrder"
      @sort="
        ({ sortField, sortOrder }) => {
          customizer.config.sortField = sortField
          customizer.config.sortOrder = sortOrder
        }
      "
      @column-reorder="
        ({ dragIndex, dropIndex }) => {
          let columns = clone(customizer.config.columns)
          const column = columns.splice(dragIndex - 1, 1)[0]
          columns.splice(dropIndex - 1, 0, column)
          customizer.config.columns = columns
        }
      "
      size="small"
    >
      <Column field="match_score" sortable class="match-column">
        <template #header>
          <span class="pi pi-verified" />
        </template>
        <template #body="{ data }">
          <BaseMatchTag
            :row="data"
            :tooltip="`Total peak intensity: ${num.peakIntensity.format(data?.sample_peak_intensity_sum)} (cps)`"
          />
        </template>
      </Column>

      <template v-for="{ field, label, kind } in customizer.config.columns" :key="field">
        <Column v-if="kind == 'standard'" :field="field" :header="label" sortable>
          <template #body="{ data }">
            <span class="field">
              <BaseCopyableField :field="data[field]" />
            </span>
          </template>
        </Column>
        <Column v-if="kind == 'custom'" field="sample_item_attributes" :header="label" sortable>
          <template #body="{ data }">
            <BaseCopyableField :field="data.sample_item_attributes[field]" />
          </template>
        </Column>
      </template>
    </DataTable>
    <i v-else style="padding-left: 3em; margin-top: 1rem; line-height: 2rem">
      Empty - no sample items
    </i>
  </div>
  <div class="spinner" v-else><ProgressSpinner strokeWidth="5px" />loading...</div>
  <!-- modals etc. -->
  <DialogSampleOp v-model:action="contextMenu.dialog.op" :item="contextMenu.row" />
  <DialogCalibration v-model:visible="contextMenu.dialog.calibration" :context="contextMenu.row" />
</template>
