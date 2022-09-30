<template>
  <the-layout-sidebar>
    <section>
      <div class="columns">
        <div class="column is-4 base-browser-sidebar">
          <the-pane-browser-target></the-pane-browser-target>
          <the-pane-browser-sample></the-pane-browser-sample>
        </div>
        <div class="column">
          <div style="padding-top: 0.5em; padding-bottom: 1em">
            <h1 style="font-size: 16px; text-align: left">
              <p>
                <b>Select calibration peaks:</b>
              </p>
            </h1>
          </div>
          <base-table
            :rows="candidateTableRows"
            :cols="candidateTableCols"
            :checkable="true"
            :searchable="true"
            :height="candidateTableHeight"
            @selectRows="selectCandidates"
          >
          </base-table>
          <div style="padding-top: 1.5em; padding-bottom: 1.5em">
            <h1 style="font-size: 16px; text-align: left">
              <p>
                <template v-if="sampleItemFocused">
                  <b
                    >Current parameters:
                    {{
                      sampleItemFocused.mz_calibration
                        ? sampleItemFocused.mz_calibration.par
                        : "undefined"
                    }}</b
                  >
                </template>
                <br />
                <template v-if="mzFit">
                  <b>Fit parameters: {{ mzFit.par }}</b>
                </template>
              </p>
            </h1>
          </div>
          <div style="padding-top: 1.5em; padding-bottom: 1.5em">
            <h1 style="font-size: 16px; text-align: left">
              <p>
                <b>Selected calibration peaks:</b>
              </p>
            </h1>
          </div>
          <base-table
            :key="selectedTableKey"
            :rows="selectedTableRows"
            :cols="selectedTableCols"
            :checkable="false"
            :searchable="false"
            :height="selectedTableHeight"
          >
          </base-table>
        </div>
      </div>

      <b-button
        @click="applyCalibration"
        style="position: fixed; right: 5em; bottom: 2em"
        icon-left="content-save"
        type="is-primary"
        :disabled="false"
        rounded
      >
        Apply to batch
      </b-button>
    </section>
  </the-layout-sidebar>
</template>

<script>
import TheLayoutSidebar from "./TheLayoutSidebar.vue";
import ThePaneBrowserSample from "./ThePaneBrowserSample.vue";
import ThePaneBrowserTarget from "./ThePaneBrowserTarget.vue";
import BaseTable from "./BaseTable.vue";

import { sync, get, call } from "vuex-pathify";

export default {
  name: "ThePageMassCalibration",
  components: {
    TheLayoutSidebar,
    ThePaneBrowserTarget,
    ThePaneBrowserSample,
    BaseTable,
  },
  data: function () {
    return {
      candidateTableCols: [
        { field: "target_compound_name", label: "Compound name" },
        { field: "target_compound_formula", label: "Compound formula" },
        { field: "target_ion_formula", label: "Ion formula" },
        { field: "mz", label: "Isotope m/z" },
        { field: "sample_peak_mz", label: "Sample m/z" },
        { field: "match_mz_error", label: "m/z error [ppm]" },
        { field: "relative_abundance", label: "Relative abundance" },
        { field: "sample_peak_height_relative", label: "Relative peak height" },
        { field: "sample_peak_height", label: "Sample peak intensity" },
        { field: "match_score", label: "Match score" },
      ],
      selectedTableCols: [
        { field: "mz", label: "Isotope m/z" },
        { field: "sample_peak_mz", label: "Pre peak m/z" },
        { field: "match_mz_error", label: "Pre m/z error [ppm]", subheading: null },
        { field: "post_mz", label: "Post peak m/z" },
        {
          field: "post_dmz",
          label: "Post m/z error [ppm]",
          subheading: null,
        },
        { field: "mz_error_diff", label: "m/z error diff", subheading: null },
      ],
      selectedTableKey: 0,
      selectedTableRows: [],
    };
  },
  created: function () {},
  computed: {
    ...get({
      batchActive: "batch/active",
      matchIsotopes: "sample/matchIsotopes",
      mzFitStats: "calibration/mzFitStats",
      sampleItemFocused: "sample/active",
      sampleItems: "batch/sampleItems",
    }),
    ...sync({
      mzFit: "calibration/mzFit",
    }),
    candidateTableHeight() {
      return "calc(30vh)";
    },
    candidateTableRows() {
      return this.matchIsotopes ?? [];
    },
    selectedTableHeight() {
      return "calc(30vh)";
    },
  },
  methods: {
    applyCalibration() {
      this.$buefy.dialog.confirm({
        title: "Calibrate items",
        message: `Apply calibration to batch ${this.batchActive.sample_batch_name}?`,
        confirmText: "Apply",
        onConfirm: () => {
          this.$api.emit(
            'calibration_mz_apply',  
            this.mzFit,
            this.sampleItems.map((item) => item.filename)
            );
        },
      });
    },
    async selectCandidates(newRows, oldRows) {
      this.mzFit = null;
      this.selectedTableRows = newRows;
      if (newRows.length > 3) {
        let peakTofs = newRows.map((row) => row.sample_peak_tof);
        let peakMzs = newRows.map((row) => row.sample_peak_mz);
        let exactMzs = newRows.map((row) => row.mz);
        await this.$api.emit(
          'calibration_mz_fit',
          peakTofs,
          peakMzs,
          exactMzs,
        );
      }
    },
  },
  watch: {
    mzFitStats: function () {
      this.selectedTableRows.forEach((row, i) => {
        row.post_mz = this.mzFitStats.post_mz[i];
        row.post_dmz = this.mzFitStats.post_dmz[i];
        row.mz_error_diff = Math.abs(row.post_dmz) - Math.abs(row.match_mz_error);
      });
      this.selectedTableCols.filter(
        (col) => col.field == "match_mz_error"
      )[0].subheading = this.mzFitStats.pre_dmz_norm;
      this.selectedTableCols.filter(
        (col) => col.field == "post_dmz"
      )[0].subheading = this.mzFitStats.post_dmz_norm;
      this.selectedTableCols.filter(
        (col) => col.field == "mz_error_diff"
      )[0].subheading =
        this.mzFitStats.post_dmz_norm - this.mzFitStats.pre_dmz_norm;
      this.selectedTableKey++;
    },
  },
};
</script>