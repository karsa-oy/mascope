<script setup>
import { inject } from 'vue'

import Button from 'primevue/button'
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'

import { BaseTabbedPanel, BaseMatchTag, BaseCopyableField } from '@/lib/base'
import { num } from '@/lib/formatters'

import { useApp } from '@/stores'

const app = useApp()

const tableHeight = inject('target-table-height')
</script>

<template>
  <BaseTabbedPanel
    label="Target Ions"
    icon="pi pi-bullseye"
    :clear="app.data.match.compound.unfocus"
    :loading="app.data.match.ion.loading"
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
    <DataTable
      :value="
        app.data.match.ion.list.filter(
          (ion) =>
            ion.target_compound_id === app.data.match.compound.focused.target_compound_id &&
            ion.target_collection_id === app.data.match.collection.focusedId
        )
      "
      dataKey="match_key"
      v-model:selection="app.data.match.ion.focused"
      selectionMode="single"
      :metaKeySelection="false"
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
      <Column header="Ion" field="target_ion_formula" sortable>
        <template #body="{ data }">
          <div :id="data.match_key" class="row" style="justify-content: flex-start">
            <span
              :class="`pi pi-chevron-${
                data.target_ion_id == app.data.match.ion.focused?.target_ion_id ? 'down' : 'right'
              }`"
              style="font-size: smaller; margin-right: 0.5rem"
            />
            <BaseCopyableField :field="data.target_ion_formula" />
          </div>
        </template>
      </Column>
      <Column header="Mechanism" field="ionization_mechanism" sortable>
        <template #body="{ data }">
          <BaseCopyableField :field="data.ionization_mechanism">
            <Button
              v-tooltip.bottom="{ value: 'Filter by mechanism', showDelay: 2000 }"
              icon="pi pi-filter"
              :severity="
                app.ui.filter.mechanism?.ionization_mechanism === data.ionization_mechanism
                  ? 'info'
                  : 'secondary'
              "
              text
              size="small"
              :class="
                app.ui.filter.mechanism?.ionization_mechanism === data.ionization_mechanism
                  ? 'active-filter'
                  : ''
              "
              @click="
                (event) => {
                  event.stopPropagation()
                  if (app.ui.filter.mechanism?.ionization_mechanism === data.ionization_mechanism) {
                    app.ui.filter.mechanism = null // Remove the filter if already applied
                  } else {
                    app.ui.filter.mechanism = {
                      ionization_mechanism: data.ionization_mechanism,
                      ionization_mechanism_id: data.ionization_mechanism_id
                    }
                  }
                }
              "
            />
          </BaseCopyableField>
        </template>
      </Column>
    </DataTable>
  </BaseTabbedPanel>
</template>

<style scoped>
.active-filter {
  visibility: visible !important;
  color: var(--p-button-text-info-color);
  opacity: 0.7;
}
</style>
