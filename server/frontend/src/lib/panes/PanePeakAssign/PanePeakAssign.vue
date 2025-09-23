<script setup>
import { ref, reactive, computed, watch, watchEffect, onUnmounted } from 'vue'
import { watchDebounced } from '@vueuse/core'

import Panel from 'primevue/panel'
import TabMenu from 'primevue/tabmenu'
import FloatLabel from 'primevue/floatlabel'
import InputText from 'primevue/inputtext'
import InputNumber from 'primevue/inputnumber'
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'
import ProgressSpinner from 'primevue/progressspinner'
import MultiSelect from 'primevue/multiselect'

import { useApp } from '@/stores'
import { api } from '@/api'
import { BaseMatchTag } from '@/lib/base'
import { PopoverTargetCompoundAdd } from '@/lib/dialogs'
import { num } from '@/lib/formatters'

import { usePreview } from './preview.js'

const app = useApp()

const preview = usePreview()

const visible = defineModel('visible')

const props = defineProps({
  height: {
    type: Number,
    required: true
  }
})

// TODO: make global params store
const chemConfig = ref(null)
const ionMechs = ref([])
const params = reactive({
  mzPrecision: null,
  formulaRange: null,
  limit: null
})
const formulaRangeModel = ref('')
const results = ref([])
const totalMatches = ref(0)
const displayedMatches = ref(0)
const loading = ref(false)

// Load  configuration from api on component creation
api.http
  .get('/params', {
    type: 'read_params'
  })
  .then(({ data }) => {
    // Store the cheminfo config
    chemConfig.value = data?.data?.params?.cheminfo_config
    // Initialize parameters with values from API response
    if (chemConfig.value) {
      params.mzPrecision = chemConfig.value.DEFAULT_MZ_PRECISION
      params.formulaRange = chemConfig.value.DEFAULT_FORMULA_RANGE
      params.limit = chemConfig.value.DEFAULT_RESULT_LIMIT
      formulaRangeModel.value = chemConfig.value.DEFAULT_FORMULA_RANGE
    }
  })
  .catch((err) => {
    console.error('Error fetching params:', err)
  })

const updateFormulaRange = () => {
  params.formulaRange = formulaRangeModel.value
}

// Set up notification handler for ChemInfo match results
const notificationHandler = app.ui.notification.on('match_cheminfo_by_mz', (payload) => {
  if (payload.status === 'error') {
    loading.value = false
    return
  }
  if (!payload) return

  // Only process results if they match current focus
  const isFocusedSample = payload?.data?.sample_item_id === app.data.sample.focusedId
  const isFocusedMz = payload?.data?.mz === app.data.peak.focused?.mz
  if (!isFocusedSample || !isFocusedMz) return

  // Process successful results
  if (payload.status === 'success') {
    if (payload.data?.data) {
      totalMatches.value = payload?.data?.total || 0
      displayedMatches.value = payload?.data?.results || 0

      results.value = payload.data.data.map((res) => {
        const existing = app.data.target.compound.list.filter(
          ({ target_compound_formula }) => target_compound_formula === res.target_compound_formula
        )
        return { ...res, existing }
      })
    }
    loading.value = false
  }
})

// Clean up event listener when component is unmounted
onUnmounted(() => {
  notificationHandler?.unmount?.()
})

// Synchronize formulaRangeModel with params.formulaRange when the latter changes
watch(
  () => params.formulaRange,
  (newValue) => {
    if (formulaRangeModel.value !== newValue) {
      formulaRangeModel.value = newValue
    }
  }
)

// Initialize ionization mechanisms and reset params to defaults when batch focus changes
watchEffect(() => {
  // Only proceed if chemConfig is loaded
  if (!chemConfig.value) return
  const ionMode = app.data.ionization.mode.list.find(
    (im) => im.ionization_mode_id === app.data.sample.focused.ionization_mode_id
  )
  ionMechs.value = ionMode.ionization_mechanism_ids.map((id) =>
    app.data.ionization.mechanism.list.find(
      ({ ionization_mechanism_id }) => id === ionization_mechanism_id
    )
  )
  params.mzPrecision = chemConfig.value.DEFAULT_MZ_PRECISION
  params.formulaRange = chemConfig.value.DEFAULT_FORMULA_RANGE
  formulaRangeModel.value = chemConfig.value.DEFAULT_FORMULA_RANGE
})

// Debounced API request that triggers when any dependency changes (single computed object `deps`)
watchDebounced(
  () => {
    // Only track dependencies if chemConfig is loaded
    if (!chemConfig.value) return {}

    return {
      peakFocused: app.data.peak.focused ? app.data.peak.focused.mz : null,
      sampleId: app.data.sample.focusedId,
      mzPrecision: params.mzPrecision,
      formulaRange: params.formulaRange,
      limit: params.limit,
      ionMechanismIds: ionMechs.value.map((m) => m.ionization_mechanism_id).join(',')
    }
  },
  // The callback function that runs 800ms after dependencies stop changing
  async (deps) => {
    // Skip if config not loaded or no peak selected
    if (!chemConfig.value || !deps.peakFocused) {
      results.value = []
      loading.value = false
      return
    }

    // Update UI to show loading state immediately
    loading.value = true
    results.value = []
    totalMatches.value = 0
    displayedMatches.value = 0

    // Make the request to start the background task
    await api.http.post(
      `/cheminfo/mz/match/sample/${deps.sampleId}`,
      {
        mz: app.data.peak.focused.mz,
        sample_item_id: deps.sampleId,
        ionization_mechanism_ids: ionMechs.value.map(
          ({ ionization_mechanism_id }) => ionization_mechanism_id
        ),
        mz_precision: deps.mzPrecision,
        formula_ranges: deps.formulaRange,
        limit: deps.limit,
        match_params: app.data.match.params.typeDefaults
      },
      {
        use: 'read',
        type: 'match_cheminfo_by_mz'
      }
    )
  },
  // Options: debounce delay, deep comparison for proper nested reactivity
  {
    debounce: computed(() => chemConfig.value.DEBOUNCE_DELAY_MS),
    deep: true
  }
)

const columns = [
  { field: 'target_compound_formula', label: 'Formula' },
  { field: 'ionization_mechanism', label: 'Ion. Mechanism' },
  { field: 'target_isotope_mz', label: 'Isotope m/z' },
  { field: 'target_isotope_mz_error_ppm', label: 'm/z error (ppm)' }
]

const expanded = ref({})
</script>

<template>
  <Panel
    class="browser"
    style="border: none; flex-grow: 1; max-width: 900px"
    :pt="{ content: { style: { padding: 0 } } }"
  >
    <template #header>
      <TabMenu
        :model="[{ label: 'Assign Peak', icon: 'pi ph ph-magnifying-glass' }]"
        style="overflow: hidden"
      />
    </template>
    <template #icons>
      <span style="opacity: 0.5" v-if="app.data.peak.focused">
        Showing {{ displayedMatches }} {{ displayedMatches === 1 ? 'match' : 'matches' }} out of
        {{ totalMatches }} potential {{ totalMatches === 1 ? 'compound' : 'compounds' }} for peak
        {{ num.mz.format(app.data.peak.focused.mz) }}
      </span>
    </template>
    <div class="col" style="gap: 1rem; align-items: stretch; max-width: 900px">
      <menu class="topbar">
        <FloatLabel style="flex-shrink: 1">
          <InputNumber v-model="params.mzPrecision" id="mzPrecision" />
          <label for="mzPrecision">m/z precision</label>
        </FloatLabel>
        <FloatLabel style="flex-shrink: 1">
          <InputNumber v-model="params.limit" id="limit" />
          <label for="limit">results limit</label>
        </FloatLabel>
        <FloatLabel style="flex-grow: 1">
          <InputText
            v-model="formulaRangeModel"
            id="formulaRange"
            fluid
            @blur="updateFormulaRange"
            @keydown.enter="updateFormulaRange"
          />
          <label for="formulaRange">formula range</label>
        </FloatLabel>
        <FloatLabel style="min-width: 100px">
          <MultiSelect
            id="ionmechs"
            v-model="ionMechs"
            dataKey="ionization_mechanism_id"
            :options="app.data.ionization.mechanism.list"
            optionLabel="ionization_mechanism"
            fluid
          />
          <label for="ionmechs">Ion. Mechanisms</label>
        </FloatLabel>
      </menu>
      <DataTable
        v-if="!loading && results.length > 0"
        :value="results"
        dataKey="target_compound_formula"
        sortField="match_score"
        :sortOrder="-1"
        scrollable
        :scrollHeight="`${height - 100}px`"
        size="small"
        v-model:expandedRows="expanded"
      >
        <Column expander />
        <Column field="target_compound_formula" header="Formula" sortable />
        <Column field="cheminfo.target_isotope_mz" header="Isotope m/z" sortable>
          <template #body="{ data }">
            {{ num.mz.format(data.cheminfo.target_isotope_mz) }}
          </template>
        </Column>
        <Column
          field="cheminfo.ionization_mechanism.ionization_mechanism"
          header="Mech."
          sortable
        />
        <Column field="cheminfo.target_isotope_mz_error_ppm" header="Error (ppm)" sortable>
          <template #body="{ data }">
            {{ num.mzError.format(data.cheminfo.target_isotope_mz_error_ppm) }}
          </template>
        </Column>
        <Column field="match_score" sortable>
          <template #header>
            <span class="pi pi-verified" v-tooltip="'Match score'" />
          </template>
          <template #body="{ data }">
            <BaseMatchTag :row="data" nofade />
          </template>
        </Column>
        <Column field="existing" sortable>
          <template #header>
            <span class="pi pi-info-circle" v-tooltip.left="'Compound info'" />
          </template>
          <template #body="{ data }">
            <span
              v-if="data.existing.length > 0"
              class="ph pi ph-database"
              v-tooltip.left="
                `Found in DB: ${data.existing
                  .map(
                    (comp) =>
                      `${comp?.target_compound_name?.length > 0 ? comp.target_compound_name : 'Unnamed'}`
                  )
                  .join(', ')}`
              "
            />
          </template>
        </Column>
        <Column>
          <template #body="{ data }">
            <PopoverTargetCompoundAdd :formula="data.target_compound_formula" />
          </template>
        </Column>
        <template #expansion="{ data }">
          <DataTable
            :value="
              data.children.map((record) => ({
                ...record,
                close: Math.abs(record.mz - app.data.peak.focused?.mz) < params.mzPrecision / 1000
              }))
            "
            dataKey="mz"
            selectionMode="single"
            v-model:selection="preview.peak"
            sortField="mz"
            size="small"
            style="margin-left: 3rem; margin-right: 10rem"
          >
            <Column field="close" sortable>
              <template #header>
                <span class="pi pi-info-circle" v-tooltip.left="'Peak info'" />
              </template>
              <template #body="{ data }">
                <span
                  class="pi ph ph-crosshair"
                  v-if="data.close"
                  v-tooltip.left="'Within tolerance of searched peak'"
                />
              </template>
            </Column>
            <Column field="relative_abundance" header="Rel. Abu." sortable>
              <template #body="{ data }">
                {{ num.relativeAbundance.format(data.relative_abundance) }}
              </template>
            </Column>
            <Column field="mz" header="Isotope m/z" sortable>
              <template #body="{ data }">
                {{ num.mz.format(data.mz) }}
              </template>
            </Column>
            <Column field="data.match_isotope_similarity" header="Similarity" sortable>
              <template #body="{ data }">
                {{ num.isotopeSimilarity.format(data.match_isotope_similarity) }}
              </template>
            </Column>
            <Column field="match_mz_error" header="Error (ppm)" sortable>
              <template #body="{ data }">
                {{ num.mzError.format(data.match_mz_error) }}
              </template>
            </Column>
            <Column field="match_score" sortable>
              <template #header>
                <span class="pi pi-verified" v-tooltip="'Match score'" />
              </template>
              <template #body="{ data }">
                <BaseMatchTag :row="data" nofade />
              </template>
            </Column>
          </DataTable>
        </template>
      </DataTable>
      <div
        v-else
        class="center"
        style="width: 100%; max-width: 900px; height: 200px"
        v-if="!app.data.peak.focused"
      >
        <div class="col" style="gap: 1rem; max-width: 45ch; text-align: center">
          <strong>
            <span class="pi ph ph-info" />
            No peak selected</strong
          >
          <i style="opacity: 0.6">
            Select peaks by clicking rows in the peak browser to the left, or by clicking the
            vertical grey peak detection lines in the spectrum chart.
          </i>
        </div>
      </div>
      <div
        v-if="app.data.peak.focused && !loading && results.length === 0"
        class="center"
        style="width: 100%; height: 220px"
      >
        <div class="col" style="gap: 1rem; max-width: 45ch; text-align: center">
          <strong>
            <span class="pi ph ph-info" />
            No results found
          </strong>
          <i style="opacity: 0.6">
            Consider checking that formula ranges account for ionization mechanisms selected.
          </i>
        </div>
      </div>
      <div v-if="loading" class="center" style="width: 100%; height: 220px">
        <div class="col">
          <ProgressSpinner />
          <strong>Loading...</strong>
        </div>
      </div>
    </div>
  </Panel>
</template>

<style scoped>
.topbar {
  justify-content: space-between;
  padding: 0;
  margin: 0;
  display: flex;
  flex-flow: row nowrap;
  gap: 1rem;
  width: 100%;
}

:deep(.p-panel-header) {
  display: flex !important;
}
</style>
