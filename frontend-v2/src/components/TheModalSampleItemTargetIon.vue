<script setup>
  import { ref, computed, watch } from 'vue'

  import ThePaneSampleSignal from './ThePaneSampleSignal.vue'
  import ThePaneFilterSettingsIon from './ThePaneFilterSettingsIon.vue'
  import BaseTagMatch from './BaseTagMatch.vue'

  
  import {
    useModalStore,
    useSampleStore,
    useVisualizationStore
  } from '@/stores'

  const sampleStore = useSampleStore()
  const modalStore = useModalStore()
  const visualizationStore = useVisualizationStore()

  // state
  const matchRating = ref(null)
  const checklist = ref({
    isotopeRating: {},
    timeseriesGoodMatch: null,
    timeseriesExpectedBehavior: null,
    comment: '',
  })


  // computed
  const modalTitle = computed(() => {
    let title = sampleStore.active ? sampleStore.active.sample_item_name : ''

    if (visualizationStore.activeIon) {
      const ionSumIntensity = formatNumber(visualizationStore.activeIon.sample_peak_area_sum)
      title += `: ${visualizationStore.activeIon.target_ion_formula} | Intensity: ${ionSumIntensity}`
    }

    return title
  })
  const submitRatingEnable = computed(() => {
    if (matchRating.value === null) return false
    if (displayChecklist.value) {
      return (
        checklist.value.timeseriesGoodMatch !== null &&
        checklist.value.timeseriesExpectedBehavior !== null
      )
    }
    return true
  })
  const displayChecklist = computed(() => {
    if (matchRating.value === '1') {
      return true
    }
    if (
      matchRating.value === '2' &&
      visualizationStore.activeIon.match_score < visualizationStore.paramPossibleMatchThreshold
    ) {
      return true
    }
    if (
      matchRating.value === '0' &&
      visualizationStore.activeIon.match_score > visualizationStore.paramPossibleMatchThreshold
    ) {
      return true
    }
    return false
  })
  const checklistLabel = computed(() => {
    if (matchRating.value === '1') {
      return 'Please provide additional information why this match is ambiguous:'
    }
    return "If your rating doesn't align with the match algorithm, please fill out the checklist below:"
  })

  // methods
  function formatNumber(value) {
    const roundedValue = Math.round(value)
    const formatter = new Intl.NumberFormat('en-US')
    return formatter.format(roundedValue)
  }
  function resetForm() {
    matchRating.value = null
    checklist.value = {
      isotopeRating: {},
      timeseriesGoodMatch: null,
      timeseriesExpectedBehavior: null,
      comment: '',
    }
    visualizationStore.visualizationStore.activeIsotopes.forEach((isotope) => {
      checklist.value.isotopeRating[isotope.mz] = 3
    })
  }
  function deactivateModalResetData() {
    modalStore.deactivate()
    resetForm()
    visualizationStore.unload()
  }
  // Function to return display text for isotope rating
  function getIsotopeRatingText(value) {
    switch (value) {
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
    }
  }
  function getThumbColor(rating) {
    switch (rating) {
      case 1:
        return '#232829' // corresponding to $cool-grey-0
      case 2:
        return '#464752' // corresponding to $cool-grey
      case 3:
        return '#b0b1ba' // corresponding to $cool-grey-light
      case 4:
        return '#94aa83' // corresponding to $moss-green-light
      case 5:
        return '#86b758' // corresponding to $success
      default:
        return '#94aa83' // corresponding to $moss-green-light
    }
  }
  function getFailedFilters(isotope) {
    let failedFilters = []
    if (Math.abs(isotope.match_mz_error) > visualizationStore.paramMzTolerance) {
      failedFilters.push({
        filter: 'm/z tolerance',
        isotopeValue: `Isotope m/z error is ${isotope.match_mz_error.toFixed(3)}`,
        threshold: visualizationStore.paramMzTolerance,
      })
    }
    if (Math.abs(isotope.match_abundance_error) > visualizationStore.paramIsotopeRatioTolerance) {
      failedFilters.push({
        filter: 'Isotope ratio tolerance',
        isotopeValue: `Match abundance error is ${isotope.match_abundance_error.toFixed(3)}`,
        threshold: visualizationStore.paramIsotopeRatioTolerance,
      })
    }
    if (isotope.sample_peak_area < visualizationStore.paramPeakMinIntensity) {
      failedFilters.push({
        filter: 'Minimum peak intensity',
        isotopeValue: `Sample peak area is ${isotope.sample_peak_area.toFixed(3)}`,
        threshold: visualizationStore.paramPeakMinIntensity,
      })
    }
    if (Math.max(isotope.match_isotope_correlation, 0) < visualizationStore.paramMinIsotopeCorrelation) {
      failedFilters.push({
        filter: 'Minimum isotope correlation',
        isotopeValue: `Match isotope correlation is ${isotope.match_isotope_correlation.toFixed(
          3,
        )}`,
        threshold: visualizationStore.paramMinIsotopeCorrelation,
      })
    }
    return failedFilters
  }
  async function submitRating() {
    let payload = {
      sample_item_id: sampleStore.active.sample_item_id,
      target_ion_id: visualizationStore.activeIon.target_ion_id,
      rating: Number(matchRating.value),
      environment: {
        mz_calibration: sampleStore.active.mz_calibration,
      },
    }
    if (displayChecklist.value) {
      payload.checklist = {
        isotopes_rating: visualizationStore.visualizationStore.activeIsotopes.map((isotope) => ({
          isotope_rating: checklist.value.isotopeRating[isotope.mz],
          target_isotope_id: isotope.target_isotope_id,
        })),
        timeseries_good_match: checklist.value.timeseriesGoodMatch === 'true',
        timeseries_expected_behavior: Number(checklist.value.timeseriesExpectedBehavior),
        comment: checklist.value.comment,
      }
    }

    await visualizationStore.submitMatchRating(payload)
    resetForm()
  }

  // watchers
  watch(visualizationStore.activeIsotopes, (newVal) => {
    if (newVal) {
      newVal.forEach((isotope) => {
        checklist.value.isotopeRating[isotope.mz] = 3
      })
    }
  }, { immediate: true })
</script>


<template>
  <section>
    <b-modal v-model:active="modalStore.sampleItemTargetIonActive" trap-focus :can-cancel="true" aria-role="dialog" aria-modal
      @close="deactivateModalResetData">
      <div class="modal-card" style="width: 100%; height: 100%">
        <header class="modal-card-head">
          <h2 class="subtitle" style="width: 100%; display: flex; justify-content: space-between">
            {{ modalTitle }}
            <base-tag-match :row="activeIon" :display-match-score="true" :tooltip="{}"></base-tag-match>
          </h2>
        </header>
        <section class="modal-card-body">
          <the-pane-sample-signal></the-pane-sample-signal>

          <!-- Ion-specific Filter Settings section -->
          <b-collapse :open="false" animation="slide">
            <template #trigger>
              <!-- <section style="padding: 0em"> -->
              <section style="display: flex; justify-content: flex-end">
                <b-button icon-right="wrench" size="is-small" @click="(props) => {
      props.open = !props.open
    }
      ">Settings
                </b-button>
              </section>
            </template>
            <the-pane-filter-settings-ion></the-pane-filter-settings-ion>
          </b-collapse>

          <!-- Match Rating section -->
          <div>
            <label class="label"> Rate this match:</label>
            <b-radio v-model="matchRating" native-value="2">Detection</b-radio>
            <b-radio v-model="matchRating" native-value="0">No detection</b-radio>
            <b-radio v-model="matchRating" native-value="1">Ambiguous</b-radio>

            <!-- Display the checklist when the rating is 'Ambiguous' or not alllign with the match algoritm -->
            <div v-if="displayChecklist">
              <label class="label" style="margin-top: 10px">
                Please check the following data for more context:</label>
              <!-- Isotopes Information Table -->
              <table class="isotopes-table">
                <thead>
                  <tr>
                    <th>Isotope m/z</th>
                    <th>Match Score</th>
                    <th>Relative Abundance</th>
                    <th>Match Filtering Thresholds</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="isotope in visualizationStore.activeIsotopes" :key="isotope.target_isotope_id">
                    <td :style="{ color: isotope.color }">
                      {{ isotope.mz }}
                    </td>
                    <td>
                      <base-tag-match :row="isotope" :display-match-score="true" :tooltip="{}"></base-tag-match>
                    </td>
                    <td>{{ isotope.relative_abundance.toFixed(2) }}</td>
                    <td>
                      <div v-if="getFailedFilters(isotope).length > 0" class="failed-filters">
                        <ul>
                          <li v-for="filter in getFailedFilters(isotope)" :key="filter.filter">
                            {{ filter.isotopeValue }}
                            <span v-if="filter.threshold !== 'N/A'">({{ filter.filter }} is {{ filter.threshold
                              }})</span>
                          </li>
                        </ul>
                      </div>
                      <div v-else>All filter parameters are within acceptable thresholds.</div>
                    </td>
                  </tr>
                </tbody>
              </table>
              <label class="label" v-text="checklistLabel"></label>
              <!-- Checklist -->
              <label class="label">1) Is there a clear peak in the signal corresponding target isotope?</label>
              <div v-for="isotope in visualizationStore.activeIsotopes" :key="isotope.target_isotope_id">
                <span :style="{ color: isotope.color }">m/z {{ isotope.mz }}</span>
                <input type="range" min="1" max="5" :value="Number(checklist.isotopeRating[isotope.mz])" @input="(event) => (checklist.isotopeRating[isotope.mz] = Number(event.target.value))
      " :style="`--thumb-color: ${getThumbColor(
      Number(checklist.isotopeRating[isotope.mz]),
    )};`" />

                <span>{{ getIsotopeRatingText(checklist.isotopeRating[isotope.mz]) }}</span>
              </div>

              <label class="label">2) Do the timeseries indicate a good match between the isotopes?</label>
              <b-radio v-model="checklist.timeseriesGoodMatch" native-value="true">Yes</b-radio>
              <b-radio v-model="checklist.timeseriesGoodMatch" native-value="false">No</b-radio>

              <label class="label">3) Do the timeseries indicate expected behavior of the target in question?</label>
              <b-radio v-model="checklist.timeseriesExpectedBehavior" native-value="2">Yes</b-radio>
              <b-radio v-model="checklist.timeseriesExpectedBehavior" native-value="0">No</b-radio>
              <b-radio v-model="checklist.timeseriesExpectedBehavior" native-value="1">Do not know</b-radio>

              <label class="label">4) Comment (optional):</label>
              <b-input type="textarea" v-model="checklist.comment" class="comment-input"></b-input>
            </div>
          </div>
        </section>
        <footer class="modal-card-foot">
          <button class="button is-success" @click="submitRating" :disabled="!submitRatingEnable">
            Submit Rating
          </button>
        </footer>
      </div>
    </b-modal>
  </section>
</template>