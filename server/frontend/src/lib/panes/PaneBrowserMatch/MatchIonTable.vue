<script setup>
import { ref, reactive, inject, computed, watch } from 'vue'

import Button from 'primevue/button'
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'
import ContextMenu from 'primevue/contextmenu'
import InputText from 'primevue/inputtext'
import Select from 'primevue/select'
import MultiSelect from 'primevue/multiselect'
import { FilterMatchMode } from '@primevue/core/api'
import { useConfirm } from 'primevue/useconfirm'

import { BaseTabbedPanel, BaseMatchTag, BaseCopyableField } from '@/lib/base'
import { PopoverTargetCompoundAdd, DialogTargetCompoundUpdate } from '@/lib/dialogs'
import MatchIsotopeTable from './MatchIsotopeTable.vue'
import { num } from '@/lib/formatters'

import { useApp } from '@/stores'

const confirm = useConfirm()
const app = useApp()

// --- State Management ---
// expandable rows state - only one ion can be expanded at a time
const expandedRows = ref({})
const expandedIonId = ref(null)
const showExpanders = ref(true)
const contextMenuRef = ref()
const dialog = reactive({ compound: false })

// --- Filtering ---
// Filters configuration for each column
const filters = ref({
  target_ion_formula: { value: null, matchMode: FilterMatchMode.CONTAINS },
  target_compound_name: { value: null, matchMode: FilterMatchMode.CONTAINS },
  target_compound_formula: { value: null, matchMode: FilterMatchMode.IN },
  ionization_mechanism: { value: null, matchMode: FilterMatchMode.EQUALS }
})

// Unique values for dropdown filters
const filterOptions = computed(() => ({
  compounds: [
    ...new Set(app.data.match.ion.list.map((ion) => ion.target_compound_formula).filter(Boolean))
  ],
  mechanisms: [
    ...new Set(app.data.match.ion.list.map((ion) => ion.ionization_mechanism).filter(Boolean))
  ]
}))

// --- Context menu configuration for ion/compound management ---
const contextRecord = ref(null) // Holds the match ion data for the context menu

const compoundLabel = computed(
  () =>
    contextRecord.value?.target_compound_name ||
    contextRecord.value?.target_compound_formula ||
    'Unknown Compound'
)

const contextMenuItems = computed(() => {
  if (!contextRecord.value) return []

  const record = contextRecord.value
  const collection = app.data.target.collection.detailed

  return [
    {
      label: `Edit compound '${compoundLabel.value}'`,
      icon: 'pi pi-pen-to-square',
      command: () => {
        dialog.compound = true
      }
    },
    {
      label: `Remove '${compoundLabel.value}' from '${collection.target_collection_name}'`,
      icon: 'pi pi-minus',
      command: () => removeCompoundFromCollection(record, collection),
      disabled: !collection
    }
  ]
})

const removeCompoundFromCollection = (ionRecord, collection) => {
  if (!collection || !ionRecord) return
  const batchCount = collection?.sample_batches_count ?? 0

  confirm.require({
    icon: 'pi pi-exclamation-triangle',
    header: `Remove target compound '${compoundLabel.value}'`,
    message: `Are you sure you want to remove compound '${compoundLabel.value}' from target collection 
    '${collection.target_collection_name}' used in ${batchCount} batches? This will require rematching the affected batches.`,
    accept: () => {
      const remainingCompoundIds = [
        ...new Set(
          app.data.match.ion.list
            .filter(
              (ion) =>
                ion.target_collection_id === collection.target_collection_id &&
                ion.target_compound_id !== ionRecord.target_compound_id
            )
            .map((ion) => ion.target_compound_id)
        )
      ]
      app.data.target.collection.update({
        target_collection_id: collection.target_collection_id,
        target_collection_name: collection.target_collection_name,
        target_collection_type: collection.target_collection_type,
        target_compound_ids: remainingCompoundIds
      })
    },
    acceptProps: { icon: 'pi pi-minus', label: 'Remove' },
    rejectProps: { label: 'Cancel', severity: 'secondary' }
  })
}

// --- Row Expansion for match isotopes level ---
const onRowExpand = (event) => {
  const ionId = event.data.target_ion_id
  if (expandedIonId.value && expandedIonId.value !== ionId) {
    expandedRows.value = {}
  }
  expandedIonId.value = ionId
  expandedRows.value = { [ionId]: true }
}

const onRowCollapse = () => {
  expandedIonId.value = null
}

const toggleExpanders = () => {
  showExpanders.value = !showExpanders.value
  if (!showExpanders.value) {
    expandedRows.value = {}
    expandedIonId.value = null
  }
}

// --- Injection & Watchers ---
const tableHeight = inject('match-table-height')

// Watch for collection changes to reset expansion state
watch(
  () => app.data.match.collection.focused,
  () => {
    expandedRows.value = {}
    expandedIonId.value = null
    contextRecord.value = null
  }
)
</script>

<template>
  <BaseTabbedPanel
    label="Target Ions"
    icon="pi pi-bullseye"
    :clear="app.data.match.collection.unfocus"
    :loading="app.data.match.ion.pending"
    :pt="
      app.ui.help.right(
        `<h1>Match Browser</h1>
        <p>Shows match ions with compound data for the selected collection. Use column filters to search and narrow results.</p>
        <p>Right click on any ion to manage its parent compound. Click the expand icon to view isotope data for that ion.</p>`
      )
    "
  >
    <template #menu>
      <PopoverTargetCompoundAdd :collection="app.data.match.collection.focused" />
      <Button
        :icon="showExpanders ? 'pi pi-eye-slash' : 'pi pi-eye'"
        v-tooltip.right="
          showExpanders ? 'Hide isotope expanders column' : 'Show isotope expanders column'
        "
        text
        size="small"
        @click="toggleExpanders"
      />
    </template>

    <DataTable
      :value="app.data.match.ion.list"
      dataKey="target_ion_id"
      v-model:selection="app.data.match.ion.focused"
      v-model:expandedRows="expandedRows"
      v-model:filters="filters"
      selectionMode="single"
      :metaKeySelection="false"
      contextMenu
      v-model:contextMenuSelection="contextRecord"
      @rowContextmenu="(event) => contextMenuRef.show(event.originalEvent)"
      @rowExpand="onRowExpand"
      @rowCollapse="onRowCollapse"
      filterDisplay="row"
      resizableColumns
      size="small"
      scrollable
      :scrollHeight="`${tableHeight}px`"
      :virtualScrollerOptions="{ itemSize: 35.74 }"
      sortField="match_score"
      :sortOrder="-1"
    >
      <template #empty>No match ions found.</template>

      <!-- Expander Column -->
      <Column v-if="showExpanders" expander style="width: 3rem" />

      <!-- Match Score Column -->
      <Column sortable sortField="match.match_score" class="match-column">
        <template #header> <span class="pi pi-verified" /> </template>
        <template #body="{ data }">
          <BaseMatchTag
            :row="data"
            :tooltip="
              data.match?.sample_peak_intensity_sum
                ? `Peak intensity: ${num.peakIntensity.format(data.match.sample_peak_intensity_sum)} (cps)`
                : 'No match data'
            "
          />
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

      <!-- Ion Formula Column -->
      <Column field="target_ion_formula" header="Ion" sortable style="min-width: 10rem">
        <template #body="{ data }">
          <div
            :id="`target-ion-${data.target_ion_id}`"
            class="row"
            style="justify-content: flex-start"
          >
            <BaseCopyableField :field="data.target_ion_formula" />
          </div>
        </template>
        <template #filter="{ filterModel, filterCallback }">
          <InputText
            v-model="filterModel.value"
            type="text"
            @input="filterCallback()"
            placeholder="Search ion..."
            size="small"
          />
        </template>
      </Column>

      <!-- Compound Column -->
      <Column field="target_compound_name" header="Compound" sortable style="min-width: 12rem">
        <template #body="{ data }">
          <BaseCopyableField :field="data.target_compound_name" />
        </template>
        <template #filter="{ filterModel, filterCallback }">
          <InputText
            v-model="filterModel.value"
            type="text"
            @input="filterCallback()"
            placeholder="Search compound..."
            size="small"
          />
        </template>
      </Column>

      <!-- Compound Formula Column -->
      <Column
        field="target_compound_formula"
        header="Compound Formula"
        sortable
        style="min-width: 10rem"
      >
        <template #body="{ data }">
          <BaseCopyableField :field="data.target_compound_formula" />
        </template>
        <template #filter="{ filterModel, filterCallback }">
          <MultiSelect
            v-model="filterModel.value"
            @change="filterCallback()"
            :options="filterOptions.compounds"
            placeholder="Select compounds..."
            size="small"
            :maxSelectedLabels="2"
            style="min-width: 10rem"
          />
        </template>
      </Column>

      <!-- Ionization Mechanism Column -->
      <Column field="ionization_mechanism" header="Mechanism" sortable style="min-width: 10rem">
        <template #body="{ data }">
          <BaseCopyableField :field="data.ionization_mechanism">
            <Button
              v-if="app.data.ionization.mechanism.focusedId !== data.ionization_mechanism_id"
              v-tooltip.bottom="'Filter by mechanism'"
              icon="pi pi-filter"
              severity="secondary"
              text
              size="small"
              @click.stop="
                app.data.ionization.mechanism.focus({
                  ionization_mechanism_id: data.ionization_mechanism_id
                })
              "
            />
            <Button
              v-else
              v-tooltip.bottom="'Clear mechanism filter'"
              icon="pi pi-filter"
              severity="info"
              text
              size="small"
              class="active-filter"
              @click.stop="app.data.ionization.mechanism.unfocus()"
            />
          </BaseCopyableField>
        </template>
        <template #filter="{ filterModel, filterCallback }">
          <Select
            v-model="filterModel.value"
            @change="filterCallback()"
            :options="filterOptions.mechanisms"
            placeholder="Any mechanism"
            size="small"
            :showClear="true"
          />
        </template>
      </Column>

      <!-- Expansion slot for match isotopes data -->
      <template #expansion="slotProps">
        <MatchIsotopeTable
          v-if="expandedIonId === slotProps.data.target_ion_id"
          :ion-id="slotProps.data.target_ion_id"
          :ion-formula="slotProps.data.target_ion_formula"
        />
      </template>
    </DataTable>

    <ContextMenu ref="contextMenuRef" :model="contextMenuItems" />
  </BaseTabbedPanel>

  <DialogTargetCompoundUpdate v-model:visible="dialog.compound" :compound="contextRecord" />
</template>

<style scoped>
.active-filter {
  visibility: visible !important;
  color: var(--p-button-text-info-color);
  opacity: 0.7;
}

/* Disable hover effects on expansion content */
:deep(.p-datatable-row-expansion) {
  background-color: var(--p-datatable-row-background) !important;
}
:deep(.p-datatable-row-expansion:hover) {
  background-color: var(--p-datatable-row-background) !important;
}
:deep(.p-datatable-row-expansion .match-isotope-container) {
  background-color: transparent !important;
}
</style>
