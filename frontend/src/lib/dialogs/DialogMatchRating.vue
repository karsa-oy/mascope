<script setup>
import { ref, reactive, computed, watch } from 'vue'

import Tabs from 'primevue/tabs'
import TabList from 'primevue/tablist'
import Tab from 'primevue/tab'
import TabPanels from 'primevue/tabpanels'
import TabPanel from 'primevue/tabpanel'
import Dialog from 'primevue/dialog'
import Rating from 'primevue/rating'
import Button from 'primevue/button'
import SelectButton from 'primevue/selectbutton'
import Textarea from 'primevue/textarea'
import ScrollPanel from 'primevue/scrollpanel'
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'

import { api } from '@/api'
import { BaseMatchTag } from '@/lib/base'
import { useApp } from '@/stores'

const app = useApp()

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
  const ionSumIntensity = peak.format(app.data.match.visualized.ion?.sample_peak_area_sum)
  return `${app.data.sample.focused?.sample_item_name}: ${app.data.match.visualized.ion?.target_ion_formula} | Intensity: ${ionSumIntensity}`
})
const checklistEnabled = computed(() => {
  const possibleMatch =
    app.data.match.visualized.ion.match_score >= app.data.match.params.current.possible_match_threshold
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
  app.data.match.visualized.isotopes.map((isotope) => {
    let failures = []
    if (Math.abs(isotope.match_mz_error) > app.data.match.params.current.mz_tolerance) {
      failures.push({
        filter: 'm/z tolerance',
        message: `Isotope m/z error is ${isotope.match_mz_error.toFixed(3)}`,
        threshold: app.data.match.params.current.mz_tolerance
      })
    }
    if (
      Math.abs(isotope.match_abundance_error) >
      app.data.match.params.current.isotope_ratio_tolerance
    ) {
      failures.push({
        filter: 'Isotope ratio tolerance',
        message: `Match abundance error is ${isotope.match_abundance_error.toFixed(3)}`,
        threshold: app.data.match.params.current.isotope_ratio_tolerance
      })
    }
    if (isotope.sample_peak_area < app.data.match.params.current.peak_min_intensity) {
      failures.push({
        filter: 'Minimum peak intensity',
        message: `Sample peak area is ${isotope.sample_peak_area.toFixed(3)}`,
        threshold: app.data.match.params.current.peak_min_intensity
      })
    }
    if (
      Math.max(isotope.match_isotope_correlation, 0) <
      app.data.match.params.current.min_isotope_correlation
    ) {
      failures.push({
        filter: 'Minimum isotope correlation',
        isotopeValue: `Match isotope correlation is ${isotope.match_isotope_correlation.toFixed(3)}`,
        threshold: app.data.match.params.current.min_isotope_correlation
      })
    }
    return { ...isotope, failures, failure_count: failures.length }
  })
)
async function submit() {
  await api.request.create({
    method: 'submitMatchRating',
    body: {
      sample_item_id: app.data.sample.focused.sample_item_id,
      target_ion_id: app.data.match.visualized.ion.target_ion_id,
      rating: props.rating,
      environment: {
        mz_calibration: app.data.sample.focused.mz_calibration
      },
      checklist: checklistEnabled.value
        ? {
            isotopes_rating: app.data.match.visualized.isotopes.map((isotope) => ({
              isotope_rating: checklist.isotopeRating[isotope.mz],
              target_isotope_id: isotope.target_isotope_id
            })),
            timeseries_good_match: checklist.timeseriesGoodMatch === 'true',
            timeseries_expected_behavior: Number(checklist.timeseriesExpectedBehavior),
            comment: checklist.comment
          }
        : null
    }
  })
  // close
  visible.value = false
}

// watchers
watch(
  computed(() => app.data.match.visualized.isotopes),
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
  app.data.match.visualized.isotopes.forEach((isotope) => {
    checklist.isotopeRating[isotope.mz] = 3
  })
}

const peak = new Intl.NumberFormat('en-US', {
  minimumFractionDigits: 0,
  maximumFractionDigits: 0
})
</script>

<template>
  <Dialog v-model:visible="visible" :header="title" style="width: 35%">
    <Tabs value="questions">
      <TabList>
        <Tab value="questions">Questions</Tab>
        <Tab value="isotopes">Isotopes</Tab>
      </TabList>
      <TabPanels>
        <TabPanel value="questions">
          <p>{{ checklistLabel }} Use the isotopes tab if you need more context.</p>
          <ScrollPanel style="width: 100%; height: 40vh">
            <!-- Checklist -->
            <p style="font-weight: bold">
              1) Is there a clear peak in the signal corresponding target isotope?
            </p>
            <div
              v-for="isotope in app.data.match.visualized.isotopes"
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
        <TabPanel value="isotopes">
          <ScrollPanel style="width: 100%; height: 40vh">
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
              <Column field="match_score" sortable class="match-column">
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
          </ScrollPanel>
        </TabPanel>
      </TabPanels>
    </Tabs>
    <menu>
      <Button label="Submit" @click="submit" :disabled="invalid" />
    </menu>
  </Dialog>
</template>
