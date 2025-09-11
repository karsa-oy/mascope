<script setup>
import { inject } from 'vue'

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
    label="Target Isotopes"
    icon="pi pi-bullseye"
    :clear="app.data.match.ion.unfocus"
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
      :value="app.data.match.visualized.isotopes"
      dataKey="target_isotope_id"
      resizableColumns
      size="small"
      scrollable
      :scrollHeight="`${tableHeight}px`"
      :virtualScrollerOptions="{ itemSize: 35.74 }"
      sortField="mz"
      :sortOrder="1"
    >
      <Column field="match_score" sortable class="match-column">
        <template #header>
          <span class="pi pi-verified" />
        </template>
        <template #body="{ data }">
          <div :id="data.match_key" />
          <BaseMatchTag
            :row="data"
            :tooltip="`Peak intensity: ${num.peakIntensity.format(data?.sample_peak_intensity)} (cps)`"
          />
        </template>
      </Column>
      <Column style="width: 4ch" />
      <Column header="mz" field="mz" style="width: 15ch" sortable>
        <template #body="{ data }">
          <BaseCopyableField :field="num.mz.format(data.mz)" />
        </template>
      </Column>
      <Column header="r.a." field="relative_abundance" sortable>
        <template #body="{ data }">
          <BaseCopyableField :field="num.relativeAbundance.format(data.relative_abundance)" />
        </template>
      </Column>
    </DataTable>
  </BaseTabbedPanel>
</template>
