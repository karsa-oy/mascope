<script setup>
import { ref, inject, computed, watch } from 'vue'

import Button from 'primevue/button'
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'
import InputText from 'primevue/inputtext'
import Select from 'primevue/select'
import MultiSelect from 'primevue/multiselect'
import { FilterMatchMode } from '@primevue/core/api'

import { BaseTabbedPanel, BaseMatchTag, BaseCopyableField } from '@/lib/base'
import { PopoverTargetCompoundAdd } from '@/lib/dialogs'
import MatchIsotopeTable from './MatchIsotopeTable.vue'
import { num } from '@/lib/formatters'
import { collectionTypeIcons } from '@/lib/constants'

import { useApp } from '@/stores'
import { useCollectionContextMenu, useIonContextMenu } from './stores'
import MatchCollectionContextMenu from './MatchCollectionContextMenu.vue'
import MatchIonContextMenu from './MatchIonContextMenu.vue'

const app = useApp()
const collectionContextMenu = useCollectionContextMenu()
const ionContextMenu = useIonContextMenu()

// --- Breadcrumb Navigation ---
const breadcrumb = computed(() => {
  const collection = app.data.match.collection.focused
  if (!collection) return null

  return {
    items: [
      {
        icon: 'pi ph ph-crosshair',
        label: 'Target Collections',
        action: () => app.data.match.collection.unfocus(),
        tooltip: 'Back to target collections'
        // No context menu on this level
      },
      {
        icon: collectionTypeIcons[collection.target_collection_type] || 'pi ph ph-target',
        label: `${collection.target_collection_name}`,
        tooltip: collection.target_collection_description
          ? `${collection.target_collection_description} (${collection.target_collection_type?.toLowerCase()})`
          : collection.target_collection_type?.toLowerCase() || 'Collection targets',
        contextMenu: {
          items: collectionContextMenu.entries.value
        },
        contextMenuHandler: (event) => {
          // Manually trigger collection context menu from breadcrumb
          collectionContextMenu.selection = collection
          collectionContextMenu.ref?.toggle(event)
        }
        // No action = current view
      }
    ]
  }
})

// --- Data & Computed ---
const mechanismMap = computed(
  () =>
    new Map(
      app.data.ionization.mechanism.list.map((m) => [
        m.ionization_mechanism,
        m.ionization_mechanism_id
      ])
    )
)

// --- State Management ---
// expandable rows state - only one ion can be expanded at a time
const expandedRows = ref({})
const expandedIonId = ref(null)
const showExpanders = ref(true)

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
    ionContextMenu.clear()
  }
)

// Watch mechanism focus and sync to dropdown filter
watch(
  () => app.data.ionization.mechanism.focused,
  (focused) => {
    if (!focused) {
      // Clear dropdown when mechanism unfocused externally (chip, etc)
      filters.value.ionization_mechanism.value = null
    }
  }
)
</script>

<template>
  <BaseTabbedPanel
    :breadcrumb="breadcrumb"
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
      v-model:contextMenuSelection="ionContextMenu.selection"
      @rowContextmenu="
        async (event) => {
          event.originalEvent.stopPropagation()
          event.originalEvent.preventDefault()
          await ionContextMenu.onClick(event)
        }
      "
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
          <BaseCopyableField :field="data.ionization_mechanism"> </BaseCopyableField>
        </template>
        <template #filter="{ filterModel, filterCallback }">
          <Select
            v-model="filterModel.value"
            @change="
              (e) => {
                filterCallback()
                e.value
                  ? app.data.ionization.mechanism.focus({
                      ionization_mechanism_id: mechanismMap.get(e.value)
                    })
                  : app.data.ionization.mechanism.unfocus()
              }
            "
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
  </BaseTabbedPanel>

  <MatchCollectionContextMenu />
  <MatchIonContextMenu />
</template>

<style scoped>
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
