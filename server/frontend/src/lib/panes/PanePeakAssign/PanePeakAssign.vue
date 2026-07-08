<script setup>
import { ref, reactive, computed, watch, watchEffect, onMounted, onUnmounted } from 'vue'
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
import Button from 'primevue/button'

import { useApp } from '@/stores'
import { api } from '@/api'
import { BaseTierTag } from '@/lib/base'
import { PopoverTargetCompoundAdd } from '@/lib/dialogs'
import { num } from '@/lib/formatters'
import { formatIsotopeFormula } from '@/lib/chem'

import { usePreview } from './preview.js'

const app = useApp()

const preview = usePreview()

const PARAMS_STORAGE_KEY = 'mascope.peakAssign.params'

function loadStoredParams() {
  try {
    const stored = localStorage.getItem(PARAMS_STORAGE_KEY)
    if (stored) return JSON.parse(stored)
  } catch {}
  return null
}

function saveParams(mzPrecision, formulaRange) {
  try {
    localStorage.setItem(PARAMS_STORAGE_KEY, JSON.stringify({ mzPrecision, formulaRange }))
  } catch {}
}

defineProps({
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
  formulaRange: null
})
const formulaRangeModel = ref('')
const results = ref([])
const totalMatches = ref(0)
const displayedMatches = ref(0)
const loading = ref(false)
const lastRequestParams = ref(null)

// Regex pattern for formula range validation: "C0-100 H0-100 Cl0-10"
// Supports:
//   - Standard elements: C0-100, Cl0-10
//   - Isotope notation: [15N]0-1, [13C]0-5
//   - Custom elements (caret prefix): ^N0-1
const ELEMENT_PATTERN = '(?:[A-Z][a-z]?|\\^[A-Z][a-z]?|\\[\\d*[A-Z][a-z]?\\])'
const RANGE_PATTERN = '\\d+-\\d+'
const FORMULA_RANGE_PATTERN = new RegExp(
  `^(${ELEMENT_PATTERN}${RANGE_PATTERN})(\\s+${ELEMENT_PATTERN}${RANGE_PATTERN})*$`
)

const isFormulaRangeValid = computed(() => {
  if (!formulaRangeModel.value) return true // Empty is handled elsewhere
  return FORMULA_RANGE_PATTERN.test(formulaRangeModel.value.trim())
})

onMounted(() => {
  // Load configuration from api on component creation
  api.http
    .get('/params', {
      type: 'read_params'
    })
    .then(({ data }) => {
      // Store the cheminfo config
      chemConfig.value = data?.data?.params?.cheminfo_config
      // Initialize parameters: prefer localStorage, fall back to API defaults
      if (chemConfig.value) {
        const stored = loadStoredParams()
        params.mzPrecision = stored?.mzPrecision ?? chemConfig.value.DEFAULT_MZ_PRECISION
        params.formulaRange = stored?.formulaRange ?? chemConfig.value.DEFAULT_FORMULA_RANGE
        formulaRangeModel.value = params.formulaRange
      }
    })
    .catch((err) => {
      console.error('Error fetching params:', err)
    })
})

const updateFormulaRange = () => {
  if (isFormulaRangeValid.value) {
    params.formulaRange = formulaRangeModel.value.trim()
  }
}

// Set up notification handler for composition match results
const notificationHandler = app.ui.notification.on('match_compositions_by_mz', (payload) => {
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

// Persist params to localStorage when they change
watch(
  () => ({ mzPrecision: params.mzPrecision, formulaRange: params.formulaRange }),
  ({ mzPrecision, formulaRange }) => {
    if (mzPrecision != null && formulaRange && FORMULA_RANGE_PATTERN.test(formulaRange.trim())) {
      saveParams(mzPrecision, formulaRange)
    }
  }
)

// Initialize ionization mechanisms and reset params to defaults when batch focus changes
watchEffect(() => {
  // Only proceed if chemConfig is loaded
  if (!chemConfig.value) return
  if (!app.data.sample.focused) return
  const ionMode = app.data.ionization.mode.list.find(
    (im) => im.ionization_mode_id === app.data.sample.focused.ionization_mode_id
  )
  ionMechs.value = ionMode.ionization_mechanism_ids.map((id) =>
    app.data.ionization.mechanism.list.find(
      ({ ionization_mechanism_id }) => id === ionization_mechanism_id
    )
  )
})

// Debounced API request that triggers when any dependency changes (single computed object `deps`)
watchDebounced(
  () => {
    // Only track dependencies if chemConfig is loaded
    if (!chemConfig.value) return {}

    return {
      searchEnabled: showSearch.value,
      peakFocused: app.data.peak.focused ? app.data.peak.focused.mz : null,
      sampleId: app.data.sample.focusedId,
      mzPrecision: params.mzPrecision,
      formulaRange: params.formulaRange,
      ionMechanismIds: ionMechs.value.map((m) => m.ionization_mechanism_id).join(',')
    }
  },
  // The callback function that runs 800ms after dependencies stop changing
  async (deps) => {
    // Only search when the user has explicitly opened it (Re-search). Otherwise
    // the inspector shows the committed assignment and we must not fire a
    // background composition search on every focused peak or isotopologue.
    if (!deps.searchEnabled) {
      results.value = []
      loading.value = false
      lastRequestParams.value = null
      return
    }
    // Skip if config not loaded or no peak selected
    if (!chemConfig.value || !deps.peakFocused || !deps.mzPrecision || !deps.formulaRange) {
      results.value = []
      loading.value = false
      lastRequestParams.value = null
      return
    }
    // Create a comparable string of current parameters
    const currentParams = JSON.stringify(deps)
    // Skip if parameters haven't changed from last request
    if (lastRequestParams.value === currentParams) {
      return
    }
    // Store current params before making request
    lastRequestParams.value = currentParams

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
        match_params: app.data.match.params.typeDefaults
      },
      {
        use: 'read',
        type: 'match_compositions_by_mz'
      }
    )
  },
  // Options: debounce delay, deep comparison for proper nested reactivity
  {
    debounce: computed(() => chemConfig.value.DEBOUNCE_DELAY_MS),
    deep: true
  }
)

function getIsotopeRows(data) {
  // Find the isotope with the highest relative abundance to use as reference
  const maxIdx = data.children.reduce(
    (maxI, r, i, arr) =>
      (r.relative_abundance ?? 0) > (arr[maxI].relative_abundance ?? 0) ? i : maxI,
    0
  )
  // Store the abundance and intensity of the main isotope with each record
  // to allow scaling peak trace heights in the preview
  const mainIsotopeAbundance = data.children[maxIdx]?.relative_abundance
  // Find the height of the main isotope peak from peak store
  const mainIsotopeIntensity =
    app.data.peak.list.find((peak) => peak.mz === data.children[maxIdx]?.sample_peak_mz)?.height ||
    0
  return data.children.map((record) => ({
    ...record,
    close: (Math.abs(record.mz - app.data.peak.focused?.mz) * 1e6) / record.mz < params.mzPrecision,
    abundance_reference: mainIsotopeAbundance,
    intensity_reference: mainIsotopeIntensity
  }))
}

// Reference-database identities the cheminfo annotation attaches to each
// candidate (data.cheminfo.known_compounds); empty for de novo-only formulas.
function knownCompoundLabel(known) {
  if (!known?.length) return ''
  const name = known[0]?.name?.length ? known[0].name : 'Unnamed'
  return known.length > 1 ? `${name} +${known.length - 1}` : name
}

function knownCompoundsTooltip(known) {
  if (!known?.length) return ''
  const names = known
    .map((k) => `${k?.name?.length ? k.name : 'Unnamed'}${k?.source ? ` (${k.source})` : ''}`)
    .join(', ')
  return `Known compound in public reference database: ${names}`
}

const expanded = ref({})

// The committed assignment for the focused peak (from the latest run). When
// present, the inspector shows it and the on-demand search is collapsed behind
// a "Re-search" toggle. See docs/dev/peak_assignment_frontend.md.
const focusedAssignment = computed(() =>
  app.data.peakAssignment.peak.forPeak(app.data.peak.focused?.peak_id)
)
const showSearch = ref(false)
watch(
  focusedAssignment,
  (assignment) => {
    showSearch.value = !assignment
  },
  { immediate: true }
)

// Arbitration / chemistry provenance (database-stage assignments): chemical
// plausibility (Seven Golden Rules), arbitration confidence, calibrated
// P(correct), and an honest tie flag.
const provenance = computed(() => focusedAssignment.value?.provenance ?? null)

// Visualize the focused assignment's isotope envelope + time series in the Fit
// view (composition-driven, so it works for untargeted winners too).
async function verifyFit() {
  // Await so `visualized.ion` is set (enabling the Fit tab) before we switch.
  await app.data.match.visualized.verifyAssignment(focusedAssignment.value)
  app.ui.tab.active = 'match'
}

const fitPercent = new Intl.NumberFormat('en-US', {
  style: 'percent',
  minimumFractionDigits: 0,
  maximumFractionDigits: 0
})
const formatFit = (value) =>
  value != null && !Number.isNaN(value) ? fitPercent.format(value) : '-'

// The isotopologue family (M0 + M+1, M+2 ...) of the focused assignment. These
// satellites are folded out of the assignments table; the inspector is where
// the envelope is shown in full.
const family = computed(() => app.data.peakAssignment.peak.familyOf(focusedAssignment.value))

// Main isotope (M0) of the family; theoretical abundances are relative to it.
const m0 = computed(
  () => family.value.find((f) => f.role === 'M0' || f.isotope_label === 'M0') ?? null
)

// Compact substitution label (e.g. "[15N]", "[81Br][2H]") from the full
// isotopologue formula; falls back to the M0/M+1 offset label when the formula
// isn't stored (untargeted satellites).
const isoLabel = (iso) =>
  iso.isotope_formula ? formatIsotopeFormula(iso.isotope_formula) : iso.isotope_label || '-'

// Theoretical (predicted) relative abundance of an isotopologue as a fraction of
// M0, recovered from the stored fields. The matcher defines
//   abundance_error = observed_rel / theoretical_rel - 1,  observed_rel = I / I(M0)
// so theoretical_rel = observed_rel / (1 + abundance_error). Exact where M0 is
// the main isotope (all CHNO species); persisting the predicted abundance would
// remove that caveat.
const theoreticalRel = (iso) => {
  const base = m0.value?.sample_peak_intensity
  if (!base || base <= 0 || iso.sample_peak_intensity == null) return null
  const observed = iso.sample_peak_intensity / base
  const denom = 1 + (iso.abundance_error ?? 0)
  return denom > 0 ? observed / denom : null
}
const relAbuFmt = new Intl.NumberFormat('en-US', {
  style: 'percent',
  minimumFractionDigits: 0,
  maximumFractionDigits: 1
})
const formatRel = (value) => (value != null ? relAbuFmt.format(value) : '-')

// Per-isotopologue match quality, mirroring the matcher's abundance x mz terms,
// to flag poorly-matched satellites (coincidental peaks in the window). M0 is
// the reference and never "poor".
const isPoorMatch = (iso) => {
  if (iso.role === 'M0' || iso.isotope_label === 'M0') return false
  const ab = iso.abundance_error != null ? 1 - Math.min(1, Math.abs(iso.abundance_error)) : 1
  const mz = iso.mz_error_ppm != null ? Math.max(0, 1 - 0.01 * Math.abs(iso.mz_error_ppm)) : 1
  return ab * mz < 0.5
}
</script>

<template>
  <Panel
    v-if="app.data.peak.list.length > 0"
    class="browser"
    style="border: none; flex-grow: 1; max-width: 900px"
    :pt="
      ({ content: { style: { padding: 0 } } },
      app.ui.help.top(`
        <h1>Peak Assignment</h1>

        <p>
        Assign a composition to the currently selected peak based on the m/z value,
        ionization mechanisms and allowed ranges of atom counts.
        </p>

        <p>
        Select peaks by clicking rows in the peak browser to the left, or by clicking
        the vertical grey peak lines in the spectrum chart.
        </p>
      `))
    "
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
      <section v-if="focusedAssignment" class="inspector">
        <div class="insp-head">
          <div class="insp-formula">
            {{ focusedAssignment.assigned_formula || 'Unassigned' }}
          </div>
          <BaseTierTag
            :tier="focusedAssignment.tier"
            :fit-score="focusedAssignment.fit_score"
            :role="focusedAssignment.role"
            :source="focusedAssignment.source"
          />
        </div>
        <div
          class="insp-sub"
          v-if="
            focusedAssignment.ion_formula ||
            focusedAssignment.isotope_label ||
            focusedAssignment.source
          "
        >
          <span v-if="focusedAssignment.ion_formula">{{ focusedAssignment.ion_formula }}</span>
          <span v-if="focusedAssignment.isotope_label">
            &middot; {{ focusedAssignment.isotope_label }}</span
          >
          <span v-if="focusedAssignment.source" class="src"> &middot; {{ focusedAssignment.source }}</span>
        </div>
        <div class="evidence">
          <div class="ev">
            <span class="k">fit</span>
            <span class="v">{{ formatFit(focusedAssignment.fit_score) }}</span>
          </div>
          <div class="ev" v-if="focusedAssignment.mz_error_ppm != null">
            <span class="k">m/z error</span>
            <span class="v">{{ num.mzError.format(focusedAssignment.mz_error_ppm) }} ppm</span>
          </div>
          <div class="ev" v-if="focusedAssignment.abundance_error != null">
            <span class="k">abund. error</span>
            <span class="v">{{
              num.relativeAbundanceError.format(focusedAssignment.abundance_error)
            }}</span>
          </div>
          <div class="ev" v-if="focusedAssignment.isotope_label">
            <span class="k">isotope</span>
            <span class="v">{{ focusedAssignment.isotope_label }}</span>
          </div>
          <div class="ev" v-if="provenance?.plausibility != null">
            <span class="k" v-tooltip.top="'Chemical plausibility (Seven Golden Rules)'"
              >plausibility</span
            >
            <span class="v">{{ formatFit(provenance.plausibility) }}</span>
          </div>
          <div class="ev" v-if="provenance?.confidence != null">
            <span class="k" v-tooltip.top="'Arbitration confidence: winner share of fit x plausibility'"
              >confidence</span
            >
            <span class="v"
              >{{ formatFit(provenance.confidence)
              }}<span v-if="provenance.is_tie" class="tie-flag" v-tooltip.top="'Runner-up too close to call'"
                >&nbsp;tie</span
              ></span
            >
          </div>
          <div class="ev" v-if="provenance?.p_correct != null">
            <span class="k" v-tooltip.top="'Calibrated probability the assignment is correct'"
              >P(correct)</span
            >
            <span class="v">{{ formatFit(provenance.p_correct) }}</span>
          </div>
        </div>
        <div v-if="family.length > 1" class="isotopologues">
          <div class="alts-label">
            Isotopologues
            <span class="alts-count" v-tooltip.top="'Predicted relative abundance (fraction of M0)'"
              >theo. abu.</span
            >
          </div>
          <div class="iso-head">
            <span>iso</span><span>m/z</span><span>ppm</span><span>abu.</span>
          </div>
          <div class="iso-rows">
            <div
              v-for="iso in family"
              :key="iso.peak_assignment_id"
              class="iso-row"
              :class="{
                current: iso.sample_peak_id === focusedAssignment.sample_peak_id,
                poor: isPoorMatch(iso)
              }"
              v-tooltip.left="
                isPoorMatch(iso)
                  ? 'Poorly matched isotopologue (abundance / m/z off) - click to focus'
                  : 'Focus this isotopologue peak'
              "
              @click="app.data.peak.focus({ peak_id: iso.sample_peak_id })"
            >
              <span
                class="iso-label"
                v-tooltip.left="iso.isotope_formula || iso.isotope_label"
                ><span v-if="isPoorMatch(iso)" class="pi ph ph-warning poor-icon" />{{
                  isoLabel(iso)
                }}</span
              >
              <span class="iso-mz">{{ num.mz.format(iso.sample_peak_mz) }}</span>
              <span class="iso-err">{{
                iso.mz_error_ppm != null ? `${num.mzError.format(iso.mz_error_ppm)}` : '—'
              }}</span>
              <span class="iso-rel">{{ formatRel(theoreticalRel(iso)) }}</span>
            </div>
          </div>
        </div>
        <div v-if="focusedAssignment.alternatives?.length" class="alts">
          <div class="alts-label">
            Close alternatives <span class="alts-count">{{ focusedAssignment.alternatives.length }}</span>
          </div>
          <div class="alts-list">
            <div v-for="(alt, i) in focusedAssignment.alternatives" :key="i" class="alt">
              <span class="f">{{ alt.assigned_formula || alt.ion_formula || '?' }}</span>
              <span class="s" v-if="alt.fit_score != null">
                fit {{ formatFit(alt.fit_score)
                }}<span v-if="alt.mz_error_ppm != null">
                  &middot; {{ num.mzError.format(alt.mz_error_ppm) }} ppm</span
                >
              </span>
            </div>
          </div>
        </div>
        <div class="insp-actions">
          <Button
            v-if="focusedAssignment.assigned_formula && focusedAssignment.ionization_mechanism_id"
            label="Verify fit"
            size="small"
            text
            icon="pi ph ph-wave-sine"
            v-tooltip.top="'Visualize the isotope envelope & time series in the Fit view'"
            @click="verifyFit"
          />
          <Button
            :label="showSearch ? 'Hide search' : 'Re-search'"
            size="small"
            text
            severity="secondary"
            icon="pi ph ph-magnifying-glass"
            @click="showSearch = !showSearch"
          />
        </div>
      </section>
      <div
        v-show="showSearch"
        class="col search-region"
        style="gap: 1rem; align-items: stretch; width: 100%"
      >
      <menu class="topbar">
        <FloatLabel style="flex: 0 0 80px">
          <InputNumber v-model="params.mzPrecision" id="mzPrecision" :min="1" :max="100" fluid />
          <label for="mzPrecision">m/z precision</label>
        </FloatLabel>
        <FloatLabel style="flex-grow: 1">
          <InputText
            v-model="formulaRangeModel"
            id="formulaRange"
            fluid
            :invalid="!isFormulaRangeValid"
            @blur="updateFormulaRange"
            @keydown.enter="updateFormulaRange"
            v-tooltip.bottom="{
              value: 'Format: Element + range, e.g. C0-100 H0-200 [15N]0-1 ^N0-1',
              showDelay: 500
            }"
          />
          <label for="formulaRange">formula range</label>
        </FloatLabel>
        <FloatLabel style="min-width: 100px; max-width: 200px">
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
        sortField="fit_score"
        :sortOrder="-1"
        scrollable
        :scrollHeight="`${height - 100}px`"
        size="small"
        v-model:expandedRows="expanded"
        :virtualScrollerOptions="{ itemSize: 35.5 }"
      >
        <Column expander />
        <Column field="target_compound_formula" header="Formula" sortable />
        <Column field="cheminfo.target_compound_unsaturation" sortable>
          <template #header>
            <span v-tooltip="{ value: 'Degree of unsaturation', showDelay: 500 }"><b>DBE</b></span>
          </template>
        </Column>
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
        <Column field="fit_score" sortable>
          <template #header>
            <span
              class="pi ph ph-seal-check"
              v-tooltip="{ value: 'Fit score & confidence tier', showDelay: 500 }"
            />
          </template>
          <template #body="{ data }">
            <BaseTierTag :tier="data.tier" :fit-score="data.fit_score" :source="data.source" />
          </template>
        </Column>
        <Column field="plausibility" sortable>
          <template #header>
            <span
              class="pi ph ph-atom"
              v-tooltip="{ value: 'Chemical plausibility (Seven Golden Rules)', showDelay: 500 }"
            />
          </template>
          <template #body="{ data }">
            {{ data.plausibility != null ? formatFit(data.plausibility) : '—' }}
          </template>
        </Column>
        <Column field="existing" sortable>
          <template #header>
            <span
              class="pi pi-info-circle"
              v-tooltip.left="{ value: 'Compound info', showDelay: 500 }"
            />
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
          <template #header>
            <span
              class="pi ph ph-flask"
              v-tooltip.left="{
                value: 'Known compound (public reference database)',
                showDelay: 500
              }"
            />
          </template>
          <template #body="{ data }">
            <span
              v-if="data.cheminfo?.known_compounds?.length"
              class="known-identity"
              v-tooltip.left="{
                value: knownCompoundsTooltip(data.cheminfo.known_compounds),
                showDelay: 300
              }"
            >
              <span class="pi ph ph-flask" />
              {{ knownCompoundLabel(data.cheminfo.known_compounds) }}
            </span>
          </template>
        </Column>
        <Column>
          <template #body="{ data }">
            <PopoverTargetCompoundAdd
              :formula="data.target_compound_formula"
              :formula-editable="false"
            />
          </template>
        </Column>
        <template #expansion="{ data }">
          <DataTable
            :value="getIsotopeRows(data)"
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
            <Column field="match_mz_error" header="Error (ppm)" sortable>
              <template #body="{ data }">
                {{ num.mzError.format(data.match_mz_error) }}
              </template>
            </Column>
          </DataTable>
        </template>
      </DataTable>
      <div
        v-else-if="!app.data.peak.focused"
        class="center"
        style="width: 100%; max-width: 900px; height: 200px"
      >
        <div class="col" style="gap: 1rem; max-width: 45ch; text-align: center">
          <strong>
            <span class="pi ph ph-info" />
            No peak selected</strong
          >
          <i style="opacity: 0.6">
            Select peaks by clicking rows in the peak browser to the left, or by clicking in the
            spectrum chart.
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
          <i style="opacity: 0.6"> Consider broadening the m/z precision or formula range. </i>
        </div>
      </div>
      <div v-if="loading" class="center" style="width: 100%; height: 220px">
        <div class="col">
          <ProgressSpinner />
        </div>
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

.known-identity {
  display: inline-flex;
  align-items: center;
  gap: 0.35rem;
  color: var(--p-primary-color);
  white-space: nowrap;
  max-width: 22ch;
  overflow: hidden;
  text-overflow: ellipsis;
}

/* Peak inspector: the committed assignment for the focused peak. Capped width
   so the isotopologue/alternatives tables don't stretch across the full pane. */
.inspector {
  display: flex;
  flex-direction: column;
  gap: 0.6rem;
  padding: 0.9rem 1rem;
  border: 1px solid var(--p-content-border-color, #e3e6ec);
  border-radius: 8px;
  background: var(--p-content-background, transparent);
  max-width: 34rem;
  align-self: start;
  width: 100%;
}
.insp-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.75rem;
}
.insp-formula {
  font-family: var(--font-mono, ui-monospace, monospace);
  font-size: 1.35rem;
  font-weight: 700;
}
.insp-sub {
  font-family: var(--font-mono, ui-monospace, monospace);
  font-size: 0.8rem;
  opacity: 0.7;
}
.insp-sub .src {
  text-transform: capitalize;
}
.evidence {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 0.4rem 1rem;
}
.ev {
  display: flex;
  flex-direction: column;
  font-family: var(--font-mono, ui-monospace, monospace);
}
.ev .k {
  font-size: 0.62rem;
  letter-spacing: 0.04em;
  text-transform: uppercase;
  opacity: 0.55;
}
.ev .v {
  font-size: 0.85rem;
  font-variant-numeric: tabular-nums;
}
.alts {
  display: flex;
  flex-direction: column;
  gap: 0.2rem;
}
.alts-label {
  font-size: 0.62rem;
  letter-spacing: 0.04em;
  text-transform: uppercase;
  opacity: 0.55;
}
.alt {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 0.6rem;
  font-family: var(--font-mono, ui-monospace, monospace);
  font-size: 0.78rem;
  padding: 0.15rem 0;
  border-bottom: 1px solid var(--p-content-border-color, #eef0f4);
}
.alt .s {
  opacity: 0.6;
  font-variant-numeric: tabular-nums;
  white-space: nowrap;
}
.insp-actions {
  display: flex;
  justify-content: flex-end;
  gap: 0.5rem;
}

/* Isotopologue envelope of the focused assignment (M0 + M+1, M+2 ...). */
.isotopologues {
  display: flex;
  flex-direction: column;
  gap: 0.1rem;
}
.iso-head,
.iso-row {
  display: grid;
  grid-template-columns: 5rem 1fr auto 3.4rem;
  gap: 0.5rem;
  align-items: baseline;
  font-family: var(--font-mono, ui-monospace, monospace);
  font-size: 0.76rem;
  padding: 0.15rem 0.3rem;
}
.iso-head {
  font-size: 0.6rem;
  letter-spacing: 0.04em;
  text-transform: uppercase;
  opacity: 0.5;
}
.iso-rows {
  display: flex;
  flex-direction: column;
  gap: 0.1rem;
  max-height: 12rem;
  overflow-y: auto;
}
.iso-row {
  border-radius: 4px;
  cursor: pointer;
  font-variant-numeric: tabular-nums;
}
.iso-row:hover {
  background: var(--p-content-hover-background, rgba(127, 127, 127, 0.12));
}
.iso-row.current {
  background: color-mix(in srgb, var(--p-primary-color, #6366f1) 14%, transparent);
}
.iso-row .iso-label {
  font-weight: 600;
  display: inline-flex;
  align-items: center;
}
.iso-row .iso-err,
.iso-row .iso-rel {
  opacity: 0.7;
  text-align: right;
}
/* Poorly-matched satellites: muted text + a warning marker, so a well-matched
   envelope reads at a glance. The current-row highlight still shows through. */
.iso-row.poor {
  color: var(--p-surface-400, #9aa2b1);
}
.poor-icon {
  color: var(--p-orange-500, #f59e0b);
  font-size: 0.68rem;
  margin-right: 0.2rem;
}
.tie-flag {
  color: var(--p-orange-500, #f59e0b);
  font-weight: 600;
  font-size: 0.72rem;
}

/* Close alternatives can be dozens of candidates: cap the height and scroll. */
.alts-list {
  display: flex;
  flex-direction: column;
  max-height: 11rem;
  overflow-y: auto;
}
.alts-count {
  font-family: var(--font-mono, ui-monospace, monospace);
  font-size: 0.6rem;
  opacity: 0.6;
  border: 1px solid var(--p-content-border-color, #e3e6ec);
  border-radius: 100px;
  padding: 0 0.35rem;
  margin-left: 0.2rem;
}
</style>
