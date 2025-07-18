<script setup>
import { ref, reactive, inject } from 'vue'

import Button from 'primevue/button'
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'
import ContextMenu from 'primevue/contextmenu'

import { BaseTabbedPanel, BaseMatchTag, BaseCopyableField } from '@/lib/base'
import { DialogTargetCollectionOp, DialogMechanismsOp } from '@/lib/dialogs'
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
  collection: null,
  mechanism: null
})

const tableHeight = inject('target-table-height')
</script>

<template v-if="collections">
  <BaseTabbedPanel
    label="Target Collections"
    icon="pi pi-bullseye"
    :loading="app.data.match.collection.loading"
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
        v-tooltip.top="'Edit mechanisms'"
        label="Edit mechanisms"
        class="hiddenlabel"
        icon="pi pi-sliders-h"
        text
        size="small"
        @click="
          () => {
            dialog.mechanism = true
          }
        "
      />
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
      dataKey="match_key"
      v-model:selection="app.data.match.collection.focused"
      selectionMode="single"
      :metaKeySelection="false"
      contextMenu
      v-model:contextMenuSelection="context.record"
      @rowContextmenu="
        (event) => {
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
      <Column header="Collection" field="target_collection_name" sortable>
        <template #body="{ data }">
          <div :id="data.match_key" class="row" style="justify-content: flex-start">
            <span
              :class="`pi pi-chevron-${
                data.target_collection_id == app.data.match.collection.focused?.target_collection_id
                  ? 'down'
                  : 'right'
              }`"
              style="font-size: smaller; margin-right: 0.5rem"
            />
            <BaseCopyableField :field="data.target_collection_name">
              <Button
                v-tooltip.bottom="{ value: 'Filter by mechanism', showDelay: 2000 }"
                icon="pi pi-filter"
                :severity="
                  app.ui.filter.collections.includes(data.target_collection_id)
                    ? 'info'
                    : 'secondary'
                "
                text
                size="small"
                :class="
                  app.ui.filter.collections
                    .map(({ target_collection_id }) => target_collection_id)
                    .includes(data.target_collection_id)
                    ? 'active-filter'
                    : ''
                "
                @click="
                  (event) => {
                    event.stopPropagation()
                    if (
                      app.ui.filter.collections
                        .map(({ target_collection_id }) => target_collection_id)
                        .includes(data.target_collection_id)
                    ) {
                      app.ui.filter.collections = app.ui.filter.collections.filter(
                        ({ target_collection_id }) =>
                          target_collection_id !== data.target_collection_id
                      ) // Remove the filter if already applied
                    } else {
                      app.ui.filter.collections.push(data)
                    }
                  }
                "
              />
            </BaseCopyableField>
          </div>
        </template>
      </Column>
    </DataTable>
    <ContextMenu ref="contextMenuRef" :model="context.menuItems" />
  </BaseTabbedPanel>
  <DialogTargetCollectionOp v-model:action="dialog.collection" :collection="context.record" />
  <DialogMechanismsOp v-model:visible="dialog.mechanism" />
</template>

<style scoped>
.active-filter {
  visibility: visible !important;
  color: var(--p-button-text-info-color);
  opacity: 0.7;
}
</style>
