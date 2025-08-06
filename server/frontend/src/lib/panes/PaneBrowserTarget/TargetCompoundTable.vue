<script setup>
import { ref, reactive, inject } from 'vue'

import DataTable from 'primevue/datatable'
import Column from 'primevue/column'
import ContextMenu from 'primevue/contextmenu'
import { useConfirm } from 'primevue/useconfirm'

import { BaseTabbedPanel, BaseMatchTag, BaseCopyableField } from '@/lib/base'
import { PopoverTargetCompoundAdd, DialogTargetCompoundUpdate } from '@/lib/dialogs'
import { num } from '@/lib/formatters'

import { useApp } from '@/stores'

const confirm = useConfirm()

const app = useApp()

const context = reactive({
  record: null,
  menuItems: [
    {
      label: 'Edit compound',
      icon: 'pi pi-pen-to-square',
      command: () => {
        dialog.compound = true
      }
    },
    {
      label: 'Remove compound',
      icon: 'pi pi-minus',
      command: () => {
        const collection = app.data.target.collection.list.find(
          (coll) => coll.target_collection_id == context.record.target_collection_id
        )
        confirm.require({
          icon: 'pi pi-exclamation-triangle',
          header: `Remove target compound '${context.record.target_compound_formula}'`,
          message: `Are you sure you want to remove the compound '${context.record.target_compound_formula}' from the '${collection.target_collection_name}' collection?`,
          accept: () => {
            app.data.target.collection.update({
              target_collection_id: collection.target_collection_id,
              target_collection_name: collection.target_collection_name,
              target_collection_type: collection.target_collection_type,
              target_compound_ids: app.data.match.compound.list
                .filter((comp) => comp.target_collection_id === collection.target_collection_id)
                .map((comp) => comp.target_compound_id)
                .filter((id) => id !== context.record.target_compound_id)
            })
          },
          acceptProps: {
            icon: 'pi pi-minus',
            label: 'Remove'
          },
          rejectProps: {
            label: 'Cancel',
            severity: 'secondary'
          }
        })
      }
    }
  ]
})
const contextMenuRef = ref()

const dialog = reactive({
  compound: null
})

const tableHeight = inject('target-table-height')
</script>

<template>
  <BaseTabbedPanel
    label="Target Compounds"
    :clear="app.data.match.collection.unfocus"
    icon="pi pi-bullseye"
    :loading="app.data.match.compound.loading"
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
      <PopoverTargetCompoundAdd :collection="app.data.match.collection.focused" />
    </template>
    <DataTable
      :value="
        app.data.match.compound.list.filter(
          (comp) => comp.target_collection_id === app.data.match.collection.focusedId
        )
      "
      dataKey="match_key"
      v-model:selection="app.data.match.compound.focused"
      selectionMode="single"
      :metaKeySelection="false"
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
      <Column header="Compound" field="target_compound_formula" sortable>
        <template #body="{ data }">
          <div :id="data.match_key" class="row" style="justify-content: flex-start">
            <span
              :class="`pi pi-chevron-${
                data.target_compound_id == app.data.match.compound.focused?.target_compound_id
                  ? 'down'
                  : 'right'
              }`"
              style="font-size: smaller; margin-right: 0.5rem"
            />
            <BaseCopyableField :field="data.target_compound_formula" />
          </div>
        </template>
      </Column>
      <Column header="Name" field="target_compound_name" sortable>
        <template #body="{ data }">
          <BaseCopyableField :field="data.target_compound_name" />
        </template>
      </Column>
    </DataTable>
    <ContextMenu ref="contextMenuRef" :model="context.menuItems" />
  </BaseTabbedPanel>
  <DialogTargetCompoundUpdate v-model:visible="dialog.compound" :compound="context.record" />
</template>

<style scoped>
.active-filter {
  visibility: visible !important;
  color: var(--p-button-text-info-color);
  opacity: 0.7;
}
</style>
