<script setup>
import { computed } from 'vue'

import DataTable from 'primevue/datatable'
import Column from 'primevue/column'
import ProgressSpinner from 'primevue/progressspinner'

import { BaseMatchTag, BaseCopyableField } from '@/lib/base'
import { num } from '@/lib/formatters'
import { formatIsotopeFormula } from '@/lib/chem'

import { useApp } from '@/stores'

const app = useApp()

// --- Computed ---
const ionFormula = () => app.data.match.visualized.ion?.target_ion_formula
const loading = computed(() => app.data.match.visualized.isotopes === null)
</script>

<template>
  <div class="isotope-table-container">
    <!-- Loading spinner -->
    <div v-if="loading">
      <ProgressSpinner strokeWidth="4" style="width: 2rem; height: 2rem" />
    </div>

    <!-- No data message -->
    <div v-else-if="!app.data.match.visualized.isotopes?.length">
      No matched isotopes found for {{ ionFormula() }}
    </div>

    <!-- Isotope data table -->
    <DataTable
      v-else
      :value="app.data.match.visualized.isotopes"
      :dataKey="(isotope) => isotope.target_isotope_id"
      selectionMode="single"
      v-model:selection="app.data.match.visualized.isotopeSelected"
      size="small"
      sortField="relative_abundance"
      :sortOrder="-1"
      scrollable
      scrollHeight="flex"
    >
      <!-- Match Score Column -->
      <Column sortable sortField="match.match_score" class="match-column">
        <template #header>
          <span class="pi ph ph-seal-percent" />
        </template>
        <template #body="{ data }">
          <BaseMatchTag
            :match-score="data.match?.match_score"
            :match-category="data.match?.match_category"
            :alarming="data.match?.alarming"
            :tooltip="
              data.match?.sample_peak_intensity
                ? `Peak intensity: ${num.peakIntensity.format(data.match.sample_peak_intensity)} (cps)`
                : 'No peak intensity data'
            "
          />
        </template>
      </Column>

      <!-- formula Column -->
      <Column header="Substitution" field="formula" sortable style="width: 8rem">
        <template #body="{ data }">
          {{ formatIsotopeFormula(data.target_isotope_formula) }}
        </template>
      </Column>

      <!-- m/z Column -->
      <Column header="m/z" field="mz" sortable style="width: 8rem">
        <template #body="{ data }">
          <BaseCopyableField :field="num.mz.format(data.mz)" />
        </template>
      </Column>

      <!-- Relative Abundance Column -->
      <Column header="r.a." field="relative_abundance" sortable style="width: 8rem">
        <template #body="{ data }">
          <BaseCopyableField :field="num.relativeAbundance.format(data.relative_abundance)" />
        </template>
      </Column>
    </DataTable>
  </div>
</template>

<style scoped>
.isotope-table-container {
  flex-shrink: 0;
  height: 100%;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  min-height: 0;
  padding: 0rem;
  width: 40%;
  min-width: 300px;
  max-width: 500px;
}

.isotope-table-container :deep(.p-datatable) {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.isotope-table-container :deep(.p-datatable-table-container) {
  flex: 1;
  min-height: 0;
  overflow: auto;
}
</style>
