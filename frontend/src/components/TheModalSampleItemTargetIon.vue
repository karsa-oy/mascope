<template>
  <section>
    <b-modal
      :active.sync="modalActive"
      trap-focus
      :can-cancel="true"
      aria-role="dialog"
      aria-modal
      @close="deactivateModalResetData"
    >
      <div class="modal-card" style="width: 100%; height: 100%">
        <header class="modal-card-head">
          <h2
            class="subtitle"
            style="width: 100%; display: flex; justify-content: space-between"
          >
            {{ modalTitle }}
            <base-tag-match
              :row="activeIon"
              :display-match-score="true"
              :tooltip="{}"
            ></base-tag-match>
          </h2>
        </header>
        <section class="modal-card-body">
          <the-pane-sample-signal></the-pane-sample-signal>

          <!-- Ion-specific Filter Settings section -->
          <b-collapse :open="false" animation="slide">
            <template #trigger>
              <!-- <section style="padding: 0em"> -->
              <section style="display: flex; justify-content: flex-end">
                <b-button
                  icon-right="wrench"
                  size="is-small"
                  @click="
                    (props) => {
                      props.open = !props.open;
                    }
                  "
                  >Settings
                </b-button>
              </section>
            </template>
            <the-pane-filter-settings-ion></the-pane-filter-settings-ion>
          </b-collapse>

          <!-- Match Rating section -->
          <div>
            <label class="label"> Rate this match:</label>
            <b-radio v-model="matchRating" native-value="2">Detection</b-radio>
            <b-radio v-model="matchRating" native-value="0"
              >No detection</b-radio
            >
            <b-radio v-model="matchRating" native-value="1">Ambiguous</b-radio>

            <!-- Display the checklist when the rating is 'Ambiguous' or not alllign with the match algoritm -->
            <div v-if="displayChecklist">
              <label class="label" style="margin-top: 10px">
                Please check the following data for more context:</label
              >
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
                  <tr
                    v-for="isotope in activeIsotopes"
                    :key="isotope.target_isotope_id"
                  >
                    <td :style="{ color: isotope.color }">
                      {{ isotope.mz }}
                    </td>
                    <td>
                      <base-tag-match
                        :row="isotope"
                        :display-match-score="true"
                        :tooltip="{}"
                      ></base-tag-match>
                    </td>
                    <td>{{ isotope.relative_abundance.toFixed(2) }}</td>
                    <td>
                      <div
                        v-if="getFailedFilters(isotope).length > 0"
                        class="failed-filters"
                      >
                        <ul>
                          <li
                            v-for="filter in getFailedFilters(isotope)"
                            :key="filter.filter"
                          >
                            {{ filter.isotopeValue }}
                            <span v-if="filter.threshold !== 'N/A'"
                              >({{ filter.filter }} is
                              {{ filter.threshold }})</span
                            >
                          </li>
                        </ul>
                      </div>
                      <div v-else>
                        All filter parameters are within acceptable thresholds.
                      </div>
                    </td>
                  </tr>
                </tbody>
              </table>
              <label class="label" v-text="checklistLabel"></label>
              <!-- Checklist -->
              <label class="label"
                >1) Is there a clear peak in the signal corresponding target
                isotope?</label
              >
              <div
                v-for="isotope in activeIsotopes"
                :key="isotope.target_isotope_id"
              >
                <span :style="{ color: isotope.color }"
                  >m/z {{ isotope.mz }}</span
                >
                <input
                  type="range"
                  min="1"
                  max="5"
                  :value="Number(checklist.isotopeRating[isotope.mz])"
                  @input="
                    (event) =>
                      (checklist.isotopeRating[isotope.mz] = Number(
                        event.target.value
                      ))
                  "
                  :style="`--thumb-color: ${getThumbColor(
                    Number(checklist.isotopeRating[isotope.mz])
                  )};`"
                />

                <span>{{
                  getIsotopeRatingText(checklist.isotopeRating[isotope.mz])
                }}</span>
              </div>

              <label class="label"
                >2) Do the timeseries indicate a good match between the
                isotopes?</label
              >
              <b-radio
                v-model="checklist.timeseriesGoodMatch"
                native-value="true"
                >Yes</b-radio
              >
              <b-radio
                v-model="checklist.timeseriesGoodMatch"
                native-value="false"
                >No</b-radio
              >

              <label class="label"
                >3) Do the timeseries indicate expected behavior of the target
                in question?</label
              >
              <b-radio
                v-model="checklist.timeseriesExpectedBehavior"
                native-value="2"
                >Yes</b-radio
              >
              <b-radio
                v-model="checklist.timeseriesExpectedBehavior"
                native-value="0"
                >No</b-radio
              >
              <b-radio
                v-model="checklist.timeseriesExpectedBehavior"
                native-value="1"
                >Do not know</b-radio
              >

              <label class="label">4) Comment (optional):</label>
              <b-input
                type="textarea"
                v-model="checklist.comment"
                class="comment-input"
              ></b-input>
            </div>
          </div>
        </section>
        <footer class="modal-card-foot">
          <button
            class="button is-success"
            @click="submitRating"
            :disabled="!submitRatingEnable"
          >
            Submit Rating
          </button>
        </footer>
      </div>
    </b-modal>
  </section>
</template>

<script>
import ThePaneSampleSignal from "./ThePaneSampleSignal.vue";
import ThePaneFilterSettingsIon from "./ThePaneFilterSettingsIon.vue";
import BaseTagMatch from "./BaseTagMatch.vue";

import { mapMutations } from "vuex";
import { call, get, sync } from "vuex-pathify";

export default {
  name: "TheModalSampleItemTargetIon",
  components: {
    ThePaneSampleSignal,
    ThePaneFilterSettingsIon,
    BaseTagMatch,
  },
  props: {},
  data: function () {
    return {
      matchRating: null,
      checklist: {
        isotopeRating: {},
        timeseriesGoodMatch: null,
        timeseriesExpectedBehavior: null,
        comment: "",
      },
    };
  },
  computed: {
    ...get({
      sampleItem: "sample/active",
      activeIon: "visualization/activeIon",
      activeIsotopes: "visualization/activeIsotopes",
      paramMzTolerance: "visualization/paramMzTolerance",
      paramMinIsotopeAbundance: "visualization/paramMinIsotopeAbundance",
      paramIsotopeRatioTolerance: "visualization/paramIsotopeRatioTolerance",
      paramPeakMinIntensity: "visualization/paramPeakMinIntensity",
      paramMinIsotopeCorrelation: "visualization/paramMinIsotopeCorrelation",
      paramProbableMatchThreshold: "visualization/paramProbableMatchThreshold",
      paramPossibleMatchThreshold: "visualization/paramPossibleMatchThreshold",
    }),
    ...sync({
      modalActive: "modal/sampleItemTargetIonActive",
    }),
    modalTitle() {
      let title = this.sampleItem ? this.sampleItem.sample_item_name : "";

      if (this.activeIon) {
        const ionSumIntensity = this.formatNumber(
          this.activeIon.sample_peak_area_sum
        );
        title += `: ${this.activeIon.target_ion_formula} | Intensity: ${ionSumIntensity}`;
      }

      return title;
    },
    submitRatingEnable() {
      if (this.matchRating === null) return false;
      if (this.displayChecklist) {
        return (
          this.checklist.timeseriesGoodMatch !== null &&
          this.checklist.timeseriesExpectedBehavior !== null
        );
      }
      return true;
    },
    displayChecklist() {
      if (this.matchRating === "1") {
        return true;
      }
      if (
        this.matchRating === "2" &&
        this.activeIon.match_score < this.paramPossibleMatchThreshold
      ) {
        return true;
      }
      if (
        this.matchRating === "0" &&
        this.activeIon.match_score > this.paramPossibleMatchThreshold
      ) {
        return true;
      }
      return false;
    },
    checklistLabel() {
      if (this.matchRating === "1") {
        return "Please provide additional information why this match is ambiguous:";
      }
      return "If your rating doesn't align with the match algorithm, please fill out the checklist below:";
    },
  },
  methods: {
    ...call({
      submitMatchRating: "visualization/submitMatchRating",
      unloadIonData: "visualization/unload",
    }),
    ...mapMutations({
      deactivateModal: "modal/deactivate",
    }),
    formatNumber(value) {
      const roundedValue = Math.round(value);
      const formatter = new Intl.NumberFormat("en-US");
      return formatter.format(roundedValue);
    },
    resetForm() {
      this.matchRating = null;
      this.checklist = {
        isotopeRating: {},
        timeseriesGoodMatch: null,
        timeseriesExpectedBehavior: null,
        comment: "",
      };
      this.activeIsotopes.forEach((isotope) => {
        this.$set(this.checklist.isotopeRating, isotope.mz, 3);
      });
    },
    deactivateModalResetData() {
      this.deactivateModal();
      this.resetForm();
      this.unloadIonData();
    },
    // Function to return display text for isotope rating
    getIsotopeRatingText(value) {
      switch (value) {
        case 1:
          return "no peak";
        case 2:
          return "weak or faint peak";
        case 3:
          return "hard to say";
        case 4:
          return "probable peak";
        case 5:
          return "clear peak";
      }
    },
    getThumbColor(rating) {
      switch (rating) {
        case 1:
          return "#232829"; // corresponding to $cool-grey-0
        case 2:
          return "#464752"; // corresponding to $cool-grey
        case 3:
          return "#b0b1ba"; // corresponding to $cool-grey-light
        case 4:
          return "#94aa83"; // corresponding to $moss-green-light
        case 5:
          return "#86b758"; // corresponding to $success
        default:
          return "#94aa83"; // corresponding to $moss-green-light
      }
    },
    getFailedFilters(isotope) {
      let failedFilters = [];
      if (Math.abs(isotope.match_mz_error) > this.paramMzTolerance) {
        failedFilters.push({
          filter: "m/z tolerance",
          isotopeValue: `Isotope m/z error is ${isotope.match_mz_error.toFixed(
            3
          )}`,
          threshold: this.paramMzTolerance,
        });
      }
      if (
        Math.abs(isotope.match_abundance_error) >
        this.paramIsotopeRatioTolerance
      ) {
        failedFilters.push({
          filter: "Isotope ratio tolerance",
          isotopeValue: `Match abundance error is ${isotope.match_abundance_error.toFixed(
            3
          )}`,
          threshold: this.paramIsotopeRatioTolerance,
        });
      }
      if (isotope.sample_peak_area < this.paramPeakMinIntensity) {
        failedFilters.push({
          filter: "Minimum peak intensity",
          isotopeValue: `Sample peak area is ${isotope.sample_peak_area.toFixed(
            3
          )}`,
          threshold: this.paramPeakMinIntensity,
        });
      }
      if (
        Math.max(isotope.match_isotope_correlation, 0) <
        this.paramMinIsotopeCorrelation
      ) {
        failedFilters.push({
          filter: "Minimum isotope correlation",
          isotopeValue: `Match isotope correlation is ${isotope.match_isotope_correlation.toFixed(
            3
          )}`,
          threshold: this.paramMinIsotopeCorrelation,
        });
      }
      return failedFilters;
    },
    async submitRating() {
      let payload = {
        sample_item_id: this.sampleItem.sample_item_id,
        target_ion_id: this.activeIon.target_ion_id,
        rating: Number(this.matchRating),
        environment: {
          mz_calibration: this.sampleItem.mz_calibration,
        },
      };
      if (this.displayChecklist) {
        payload.checklist = {
          isotopes_rating: this.activeIsotopes.map((isotope) => ({
            isotope_rating: this.checklist.isotopeRating[isotope.mz],
            target_isotope_id: isotope.target_isotope_id,
          })),
          timeseries_good_match: this.checklist.timeseriesGoodMatch === "true",
          timeseries_expected_behavior: Number(
            this.checklist.timeseriesExpectedBehavior
          ),
          comment: this.checklist.comment,
        };
      }

      await this.submitMatchRating(payload);
      this.resetForm();
    },
  },
  watch: {
    activeIsotopes: {
      immediate: true,
      handler(newVal) {
        if (newVal) {
          newVal.forEach((isotope) => {
            this.$set(this.checklist.isotopeRating, isotope.mz, 3);
          });
        }
      },
    },
  },
};
</script>
