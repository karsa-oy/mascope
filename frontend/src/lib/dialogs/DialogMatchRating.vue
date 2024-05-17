<script setup>
import { ref, reactive, computed, watch } from 'vue'

import TabView from 'primevue/tabview'
import TabPanel from 'primevue/tabpanel'
import Dialog from 'primevue/dialog'
import Rating from 'primevue/rating'
import SelectButton from 'primevue/selectbutton'
import Textarea from 'primevue/textarea'

import { BaseMatchTag } from '@/lib/base'
import { useSampleStore, useVisualizationStore } from '@/stores'

const sampleStore = useSampleStore()
const visualizationStore = useVisualizationStore()

const visible = defineModel('visible')

const props = defineProps({
  rating: {
    type: Number,
    required: true
  }
})

// state
const checklist = reactive({
  isotopeRating: {},
  timeseriesGoodMatch: null,
  timeseriesExpectedBehavior: null,
  comment: ''
})

const expandedIsotopes = ref()

// computed
const title = computed(() => {
  const ionSumIntensity = peak.format(visualizationStore.activeIon?.sample_peak_area_sum)
  return `${sampleStore.active?.sample_item_name}: ${visualizationStore.activeIon?.target_ion_formula} | Intensity: ${ionSumIntensity}`
})
const checklistEnabled = computed(() => {
  const possibleMatch =
    visualizationStore.activeIon.match_score >= visualizationStore.paramPossibleMatchThreshold
  return (
    (props.rating === '0' && possibleMatch) ||
    props.rating === '1' ||
    (props.rating === '2' && !possibleMatch)
  )
})
const checklistLabel = computed(() =>
  props.rating === '1'
    ? 'Why do you find this match ambiguous?'
    : "Your rating didn't align with our algorithm, could you help us understand why?"
)
const invalid = computed(
  () => checklist.timeseriesGoodMatch === null || checklist.timeseriesExpectedBehavior === null
)

const isotopes = computed(() =>
  visualizationStore.activeIsotopes.map((isotope) => {
    let failures = []
    if (Math.abs(isotope.match_mz_error) > visualizationStore.paramMzTolerance) {
      failures.push({
        filter: 'm/z tolerance',
        message: `Isotope m/z error is ${isotope.match_mz_error.toFixed(3)}`,
        threshold: visualizationStore.paramMzTolerance
      })
    }
    if (Math.abs(isotope.match_abundance_error) > visualizationStore.paramIsotopeRatioTolerance) {
      failures.push({
        filter: 'Isotope ratio tolerance',
        message: `Match abundance error is ${isotope.match_abundance_error.toFixed(3)}`,
        threshold: visualizationStore.paramIsotopeRatioTolerance
      })
    }
    if (isotope.sample_peak_area < visualizationStore.paramPeakMinIntensity) {
      failures.push({
        filter: 'Minimum peak intensity',
        message: `Sample peak area is ${isotope.sample_peak_area.toFixed(3)}`,
        threshold: visualizationStore.paramPeakMinIntensity
      })
    }
    if (
      Math.max(isotope.match_isotope_correlation, 0) < visualizationStore.paramMinIsotopeCorrelation
    ) {
      failures.push({
        filter: 'Minimum isotope correlation',
        isotopeValue: `Match isotope correlation is ${isotope.match_isotope_correlation.toFixed(3)}`,
        threshold: visualizationStore.paramMinIsotopeCorrelation
      })
    }
    return { ...isotope, failures, failure_count: failures.length }
  })
)
async function submit() {
  await visualizationStore.submitMatchRating({
    sample_item_id: sampleStore.active.sample_item_id,
    target_ion_id: visualizationStore.activeIon.target_ion_id,
    rating: props.rating,
    environment: {
      mz_calibration: sampleStore.active.mz_calibration
    },
    checklist: checklistEnabled.value
      ? {
          isotopes_rating: visualizationStore.activeIsotopes.map((isotope) => ({
            isotope_rating: checklist.isotopeRating[isotope.mz],
            target_isotope_id: isotope.target_isotope_id
          })),
          timeseries_good_match: checklist.timeseriesGoodMatch === 'true',
          timeseries_expected_behavior: Number(checklist.timeseriesExpectedBehavior),
          comment: checklist.comment
        }
      : null
  })
  // close
  visible.value = false
}

// watchers
watch(
  computed(() => visualizationStore.activeIsotopes),
  (isotopes) => {
    if (isotopes) {
      isotopes.forEach((isotope) => {
        checklist.isotopeRating[isotope.mz] = 3
      })
    }
  },
  { immediate: true }
)

watch(visible, init)
function init(active) {
  if (!active) return
  checklist.isotopeRating = {}
  checklist.timeseriesGoodMatch = null
  checklist.timeseriesExpectedBehavior = null
  checklist.comment = ''
  visualizationStore.activeIsotopes.forEach((isotope) => {
    checklist.isotopeRating[isotope.mz] = 3
  })
}

const peak = new Intl.NumberFormat('en-US', {
  minimumFractionDigits: 0,
  maximumFractionDigits: 0
})
</script>

<template>
  <Dialog v-model:visible="visible" :header="title" style="max-width: 800px">
    <TabView>
      <TabPanel header="Questions">
        <p>{{ checklistLabel }} Use the isotopes tab if you need more context.</p>
        <ScrollPanel style="width: 100%; height: 40vh">
          <!-- Checklist -->
          <p style="font-weight: bold">
            1) Is there a clear peak in the signal corresponding target isotope?
          </p>
          <div
            v-for="isotope in visualizationStore.activeIsotopes"
            :key="isotope.target_isotope_id"
            class="row"
            style="margin: 1rem; justify-content: flex-start; gap: 3rem"
          >
            <strong :style="{ color: isotope.color }">m/z {{ isotope.mz }}</strong>
            <Rating v-model="checklist.isotopeRating[isotope.mz]" />
            <span>{{
              (() => {
                switch (checklist.isotopeRating[isotope.mz]) {
                  case 1:
                    return 'no peak'
                  case 2:
                    return 'weak or faint peak'
                  case 3:
                    return 'hard to say'
                  case 4:
                    return 'probable peak'
                  case 5:
                    return 'clear peak'
                  default:
                    return ''
                }
              })()
            }}</span>
          </div>
          <p style="font-weight: bold">
            2) Do the timeseries indicate a good match between the isotopes?
          </p>
          <SelectButton
            v-model="checklist.timeseriesGoodMatch"
            :options="[
              { label: 'Yes', value: true },
              { label: 'No', value: false }
            ]"
            optionLabel="label"
            dataKey="label"
            aria-labelledby="basic"
          />
          <p style="font-weight: bold">
            3) Do the timeseries indicate expected behavior of the target in question?
          </p>
          <SelectButton
            v-model="checklist.timeseriesExpectedBehavior"
            :options="[
              { label: 'Yes', value: 2 },
              { label: 'No', value: 0 },
              { label: `Don't know`, value: 1 }
            ]"
            optionLabel="label"
            dataKey="label"
            aria-labelledby="basic"
          />
          <hr style="margin: 2rem 0; max-width: 500px" />
          <p>Any other comments? (optional)</p>
          <Textarea v-model="checklist.comment" autoResize cols="60" rows="5" />
        </ScrollPanel>
      </TabPanel>
      <TabPanel header="Isotopes">
        <DataTable
          :value="isotopes"
          dataKey="target_isotope_id"
          sortField="match_score"
          :sortOrder="-1"
          scrollable
          scrollHeight="300px"
          v-model:expandedRows="expandedIsotopes"
        >
          <Column expander style="width: 3ch" />
          <Column field="match_score" sortable class="k-match-column">
            <template #header>
              <span class="pi pi-verified" />
            </template>
            <template #body="{ data }">
              <BaseMatchTag
                :row="data"
                :tooltip="`Peak intensity: ${peak.format(data?.sample_peak_area_sum)}`"
              />
            </template>
          </Column>
          <Column style="width: 4ch" />
          <Column header="mz" field="mz" style="width: 15ch" sortable>
            <template #body="{ data }">
              {{ peak.format(data.mz) }}
            </template>
          </Column>
          <Column header="r.a." field="relative_abundance" sortable>
            <template #body="{ data }">
              {{ peak.format(data.relative_abundance) }}
            </template>
          </Column>
          <Column header="Failures" field="failure_count" sortable />
          <template #expansion="{ data }">
            <section style="padding-left: 3rem">
              <ul v-if="data.failures.length">
                <li v-for="filter in data.failures" :key="filter.filter">
                  {{ filter.message }}
                  <span v-if="filter.threshold !== 'N/A'">
                    ({{ filter.filter }} is {{ filter.threshold }})
                  </span>
                </li>
              </ul>
              <p v-else>No failures detected</p>
            </section>
          </template>
        </DataTable>
      </TabPanel>
    </TabView>
    <menu>
      <Button label="Submit" @click="submit" :disabled="invalid" />
    </menu>
  </Dialog>
</template>
