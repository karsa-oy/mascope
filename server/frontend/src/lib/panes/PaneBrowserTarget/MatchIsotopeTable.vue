<script setup>
import { ref, onMounted } from 'vue'

import DataTable from 'primevue/datatable'
import Column from 'primevue/column'
import ProgressSpinner from 'primevue/progressspinner'

import { BaseMatchTag, BaseCopyableField } from '@/lib/base'
import { num } from '@/lib/formatters'
import { api } from '@/api'

import { useApp } from '@/stores'

const app = useApp()

// --- Props ---
const props = defineProps({
  ionId: {
    type: String,
    required: true
  },
  ionFormula: {
    type: String,
    default: ''
  }
})

// --- State ---
const isotopeData = ref([])
const loading = ref(false)

// --- API ---
/**
 * Load isotope data for the specified ion
 */
const loadIsotopes = async () => {
  if (!props.ionId) return

  try {
    loading.value = true
    const sampleId = app.data.sample.focusedId
    const batchId = app.data.batch.focusedId

    const params = { target_ion_id: props.ionId }
    if (sampleId) {
      params.sample_item_id = sampleId
    } else if (batchId) {
      params.sample_batch_id = batchId
    }

    isotopeData.value =
      (await api.http.get('/match/records/isotope', {
        params,
        use: 'read',
        type: 'load_match_isotope_records'
      })) || []
  } catch (error) {
    console.error('Failed to load isotopes:', error)
    isotopeData.value = []
  } finally {
    loading.value = false
  }
}

// --- Lifecycle ---
onMounted(() => {
  loadIsotopes()
})
</script>

<template>
  <div style="padding: 0.5rem">
    <!-- Loading spinner -->
    <div v-if="loading">
      <ProgressSpinner strokeWidth="4" style="width: 2rem; height: 2rem" />
    </div>

    <!-- No data message -->
    <div v-else-if="!isotopeData.length">No isotopes found for {{ ionFormula }}</div>

    <!-- Isotope data table -->
    <DataTable
      v-else
      :value="isotopeData"
      :dataKey="(isotope) => isotope.target_isotope_id"
      size="small"
      sortField="mz"
      :sortOrder="1"
    >
      <!-- Match Score Column -->
      <Column field="match_score" sortable class="match-column">
        <template #header>
          <span class="pi pi-verified" />
        </template>
        <template #body="{ data }">
          <BaseMatchTag
            :row="data"
            :tooltip="
              data.match?.sample_peak_intensity
                ? `Peak intensity: ${num.peakIntensity.format(data.match.sample_peak_intensity)} (cps)`
                : 'No peak intensity data'
            "
          />
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

      <!-- Resolution Column -->
      <Column header="Resolution" field="resolution" sortable>
        <template #body="{ data }">
          <BaseCopyableField
            :field="
              data.resolution ? num.resolution?.format?.(data.resolution) || data.resolution : 'N/A'
            "
          />
        </template>
      </Column>
    </DataTable>
  </div>
</template>
