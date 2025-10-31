<script setup>
import { inject, computed, watch } from 'vue'

import Button from 'primevue/button'
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'

import { BaseTabbedPanel, BaseMatchTag, BaseCopyableField } from '@/lib/base'
import { num } from '@/lib/formatters'
import { collectionTypeIcons } from '@/lib/constants'

import { useApp } from '@/stores'
import { useCollectionContextMenu } from './stores'
import MatchCollectionContextMenu from './MatchCollectionContextMenu.vue'

const app = useApp()
const contextMenu = useCollectionContextMenu()

const tableHeight = inject('match-table-height')

// Breadcrumb configuration - simple single level
const breadcrumb = computed(() => ({
  items: [
    {
      icon: 'pi ph ph-crosshair',
      label: 'Target Collections',
      disabled: true,
      tooltip: null
      // No action - this is the current view
    }
  ]
}))
</script>

<template>
  <BaseTabbedPanel
    :breadcrumb="breadcrumb"
    :loading="app.data.match.collection.pending"
    :contextMenu="contextMenu"
    :pt="
      app.ui.help.right(`
        <h1>Target Browser: Collections</h1>

        <p>Shows the target collections associated
        with the currently selected batch, and provides
        features for managing them.</p>

        <p>
        Click on a collection to view its targets.
        </p>

        <p>
        Right click on collections to edit them or add
        them to other batches.
        </p>

        <p>
        Click on the <span class='pi pi-plus'></span> button (top right)
        to create a new target collection.
        </p>
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
        @click="contextMenu.dialog.op = 'create'"
      />
    </template>
    <DataTable
      :value="app.data.match.collection.list"
      dataKey="target_collection_id"
      v-model:selection="app.data.match.collection.focused"
      selectionMode="single"
      :metaKeySelection="false"
      contextMenu
      v-model:contextMenuSelection="contextMenu.selection"
      @rowContextmenu="
        async (event) => {
          event.originalEvent.stopPropagation()
          event.originalEvent.preventDefault()
          await contextMenu.onClick(event)
        }
      "
      resizableColumns
      size="small"
      scrollable
      :scrollHeight="`${tableHeight}px`"
      :virtualScrollerOptions="{ itemSize: 35.74 }"
      sortField="match.match_score"
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
              :class="collectionTypeIcons[data.target_collection_type]"
              v-tooltip.top="data.target_collection_type.toLowerCase()"
              style="margin-right: 0.5rem"
            />
            <BaseCopyableField :field="data.target_collection_name" />
          </div>
        </template>
      </Column>
    </DataTable>
  </BaseTabbedPanel>
  <MatchCollectionContextMenu />
</template>

<style scoped>
.active-filter {
  visibility: visible !important;
  color: var(--p-button-text-info-color);
  opacity: 0.7;
}
</style>
