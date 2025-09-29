<script setup>
import { computed, watch } from 'vue'

import { useWindowSize } from '@vueuse/core'

import DataTable from 'primevue/datatable'
import Column from 'primevue/column'
import { useConfirm } from 'primevue/useconfirm'

import { BaseTabbedPanel, BaseMatchTag, BaseCopyableField } from '@/lib/base'
import { DialogSampleOp, DialogCalibration } from '@/lib/dialogs'
import { clone } from '@/lib/utils'
import { num } from '@/lib/formatters'
import { useApp } from '@/stores'

import SampleTableCustomizer from './SampleTableCustomizer.vue'
import SampleContextMenu from './SampleContextMenu.vue'
import { useSampleContextMenu, useCustomizerPopover, useBatchStatus } from './stores'

const confirm = useConfirm()
const app = useApp()

const customizer = useCustomizerPopover()
const contextMenu = useSampleContextMenu()

const batch = computed(() => app.data.batch.focused)
const samples = computed(
  () =>
    app.data.sample.list?.filter((sample) => sample.sample_batch_id == app.data.batch.focusedId) ??
    []
)

const batchStatus = computed(() => {
  if (!batch.value) return null

  const batchStatusStore = useBatchStatus()
  return {
    status: batch.value.status,
    config: batchStatusStore.config,
    onRematch: () => app.data.batch.rematch({ sample_batch_id: batch.value.sample_batch_id })
  }
})

const formatter = new Intl.NumberFormat('en-US', {
  minimumFractionDigits: 2,
  maximumFractionDigits: 2
})

/**
 * Utility function to allow scrolling to samples in the watchers below
 *
 * A lock prevents race conditions, especially if later other watchers are added.
 */
let lock = false
function scrollTo(sampleId) {
  if (!lock && sampleId) {
    lock = true
    setTimeout(() => {
      document.getElementById(sampleId)?.scrollIntoViewIfNeeded()
      lock = false
    }, 1000)
  }
}

watch(
  () => app.data.sample.focusedId,
  (sampleId, oldSampleId) => {
    if (sampleId !== oldSampleId) {
      scrollTo(sampleId)
    }
  }
)

const { height } = useWindowSize()
const padding = 100
const tableHeight = computed(() => ((height.value - padding) * app.ui.split.top) / 100 - 50)
</script>

<template>
  <BaseTabbedPanel
    label="Samples"
    icon="pi pi-tags"
    :clear="app.data.batch.unfocus"
    :contextMenu="contextMenu"
    :loading="app.data.sample.pending"
    :status="batchStatus"
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
      <SampleTableCustomizer />
    </template>
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
      resizableColumns
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
      scrollable
      :scrollHeight="`${tableHeight}px`"
      :virtualScrollerOptions="{ itemSize: 35.74 }"
      :pt="{ bodyRow: ({ context }) => ({ id: samples[context.index]?.sample_item_id }) }"
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
    <!-- modals etc. -->
    <DialogSampleOp v-model:action="contextMenu.dialog.op" :item="contextMenu.row" />
    <DialogCalibration
      v-model:visible="contextMenu.dialog.calibration"
      :context="contextMenu.row"
    />
    <SampleContextMenu />
  </BaseTabbedPanel>
</template>
