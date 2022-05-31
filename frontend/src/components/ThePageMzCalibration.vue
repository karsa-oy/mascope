<template>
  <the-layout-sidebar>
    <section>
      <div class="columns">
        <div class="column is-3 base-browser-sidebar">
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
              :searchable="false"
              :height="candidateTableHeight"
              @selectRows="selectCandidates"
            >
            </base-table>
            <div style="padding-top: 1.5em; padding-bottom: 1.5em">
              <h1 style="font-size: 16px; text-align: left">
                <p>
                  <template v-if="itemFocused">
                    <b>Current parameters: {{ itemFocused.mz_calibration.par }}</b>
                  </template>
                  <br>
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
        Apply Calibration
      </b-button>
    </section>
  </the-layout-sidebar>
</template>

<script>
import TheLayoutSidebar from "./TheLayoutSidebar";
import ThePaneBrowserSample from "./ThePaneBrowserSample";
import ThePaneBrowserTarget from "./ThePaneBrowserTarget";
import BaseTable from "./BaseTable";

import { bindState } from "$lib/store";
import { mapActions, mapMutations } from "vuex";

export default {
  name: "ThePageMassCalibration",
  components: {
    TheLayoutSidebar,
    ThePaneBrowserTarget,
    ThePaneBrowserSample,
    BaseTable,
  },
  data: function() {
    return {
      candidateTableCols: [
        { field: "targetCompoundName", label: "Compound name" },
        { field: "targetCompoundFormula", label: "Compound formula" },
        { field: "targetIonMech", label: "Ionization mechanism" },
        { field: "targetIonFormula", label: "Ion formula" },
        { field: "mz", label: "Isotope m/z" },
        { field: "samplePeakMz", label: "Sample m/z" },
        { field: "mzError", label: "m/z error [ppm]" },
        { field: "relAbu", label: "Relative abundance" },
        { field: "relPeakHeight", label: "Relative peak height" },
        { field: "samplePeakHeight", label: "Sample peak intensity" },
        { field: "matchScore", label: "Match score" },
      ],
      candidateTableHeight: "calc(30vh)",
      selectedTableCols: [
        { field: "mz", label: "Isotope m/z" },
        { field: "samplePeakMz", label: "Pre peak m/z" },
        { field: "mzError", label: "Pre m/z error [ppm]", subheading: null },
        { field: "fitMz", label: "Post peak m/z" },
        { field: "fitMzError", label: "Post m/z error [ppm]", subheading: null },
        { field: "mzErrorDiff", label: "m/z error diff", subheading: null },
      ],
      selectedTableKey: 0,
      selectedTableRows: [],
    }
  },
  created: function() {
  },
  computed: {
    ...bindState({
      mzFit: "calibration/mzFit",
      mzFitStats: "calibration/mzFitStats",
      itemFocused: "sample/item/focus/row",
      itemsSelected: "sample/item/selection/rows",
    }),
    candidateTableRows() {
      if (!this.itemFocused) return [];
      return this.$store.getters["match/rating/rows"]({
        level: "isotope",
        selected: true,
      }).filter((row) => row.sampleItemId === this.itemFocused.id);
    },
    selectedTableHeight() {
      return "calc(30vh)";
    },
  },
  methods: {
    ...mapActions({
      calibrateItems: "calibration/calibrateItems",
    }),
    ...mapMutations({
      $mzFitRequest: "calibration/MZ_FIT_REQUEST",
    }),
    applyCalibration() {
      this.$buefy.dialog.confirm({
        title: "Calibrate items",
        message: `Apply calibration to ${this.itemsSelected.length} selected items?`,
        confirmText: "Apply",
        onConfirm: () => {
          this.calibrateItems({items: this.itemsSelected, fit: this.mzFit});
          },
      });
    },
    selectCandidates(rows) {
      this.mzFit = null;
      this.selectedTableRows = rows;
      if (rows.length > 3) {
        let peakTofs = rows.map(row => row.samplePeakTof);
        let peakMzs = rows.map(row => row.samplePeakMz);
        let exactMzs = rows.map(row => row.mz);
        this.$mzFitRequest({
          peakTofs,
          peakMzs,
          exactMzs
        });
      }
    },
  },
  watch: {
    mzFitStats: function() {
      this.selectedTableRows.forEach( (row, i) => {
        row.fitMz = this.mzFitStats.fitMz[i];
        row.fitMzError = this.mzFitStats.fitMzError[i];
        row.mzErrorDiff = Math.abs(row.fitMzError) - Math.abs(row.mzError);
      });
      this.selectedTableCols.filter(
        col => col.field == "mzError"
        )[0].subheading = this.mzFitStats.preDmzNorm;
      this.selectedTableCols.filter(
        col => col.field == "fitMzError"
        )[0].subheading = this.mzFitStats.postDmzNorm;
      this.selectedTableCols.filter(
        col => col.field == "mzErrorDiff"
        )[0].subheading = (
          this.mzFitStats.postDmzNorm - this.mzFitStats.preDmzNorm
          );
      this.selectedTableKey++;
    },
  }
};
</script>