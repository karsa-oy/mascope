<script setup>
import { ref, computed, watch, nextTick } from 'vue'

import { useWindowSize } from '@vueuse/core'

import DataTable from 'primevue/datatable'
import Column from 'primevue/column'

import { BaseTabbedPanel, BaseMatchTag, BaseCopyableField } from '@/lib/base'
import { DialogSampleOp, DialogCalibration } from '@/lib/dialogs'
import { clone } from '@/lib/utils'
import { num } from '@/lib/formatters'
import { useApp } from '@/stores'

import SampleTableCustomizer from './SampleTableCustomizer.vue'
import SampleContextMenu from './SampleContextMenu.vue'
import { useSampleContextMenu, useCustomizerPopover, useBatchStatus } from './stores'

const app = useApp()
// Ref to access DataTable for programmatic scrolling
const sampleTable = ref(null)

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

/**
 * Scroll to sample in virtual scroller only if not already visible.
 * Checks visibility within the DataTable's scroll container, not window.
 */
let scrollLock = false
async function scrollToSample(sampleId) {
  if (!scrollLock && sampleId && sampleTable.value) {
    scrollLock = true

    await nextTick()

    const scrollContainer = sampleTable.value.$el.querySelector('.p-virtualscroller')

    if (!scrollContainer) {
      scrollLock = false
      return
    }

    // Check if element already exists and is visible in scroll container
    const existingElement = document.getElementById(sampleId)
    if (existingElement) {
      const containerRect = scrollContainer.getBoundingClientRect()
      const elementRect = existingElement.getBoundingClientRect()

      // Check if element is within the scroll container's visible area
      const isVisible =
        elementRect.top >= containerRect.top && elementRect.bottom <= containerRect.bottom

      if (isVisible) {
        // Already visible in container, no scroll needed
        scrollLock = false
        return
      }
    }

    const sampleIndex = samples.value.findIndex((s) => s.sample_item_id === sampleId)

    if (sampleIndex === -1) {
      scrollLock = false
      return
    }

    const itemSize = 35.74
    const scrollTop = sampleIndex * itemSize

    // Scroll container to render the row
    scrollContainer.scrollTop = scrollTop

    // Wait for render, then scroll into view using nearest edge
    setTimeout(() => {
      const element = document.getElementById(sampleId)
      if (element) {
        element.scrollIntoView({ behavior: 'smooth', block: 'nearest' })
      }
      scrollLock = false
    }, 100)
  }
}

watch(
  () => app.data.sample.selectedIds,
  (newSelection) => {
    if (!newSelection) return
    let targetSampleId = null
    if (newSelection.length === 1) {
      targetSampleId = app.data.sample.focusedId
    }
    if (newSelection.length > 1) {
      const selectedIndices = app.data.sample.selectedIds
        .map((id) => samples.value.findIndex((s) => s.sample_item_id === id))
        .filter((idx) => idx !== -1)

      if (selectedIndices.length > 0) {
        const firstIndex = Math.min(...selectedIndices)
        targetSampleId = samples.value[firstIndex].sample_item_id
      }
    }
    scrollToSample(targetSampleId)
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
    :back-label="'Back to workspaces'"
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
      ref="sampleTable"
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
                ? `Total peak intensity: ${num.peakIntensity.format(data.match.sample_peak_intensity_sum)} (cps)`
                : 'No peak intensity data'
            "
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
