<template>
  <section style="padding: 1em">
    <!-- <h2 class="subtitle">Ion-specific filter parameters</h2> -->
    <base-param-field
      label="m/z tolerance [ppm]"
      path="visualization/paramMzTolerance"
      @paramChange="reloadVisualization"
      :range="{ min: 0, max: 100, step: 1 }"
    >
    </base-param-field>
    <base-param-field
      label="Minimum isotope abundance"
      path="visualization/paramMinIsotopeAbundance"
      @paramChange="reloadVisualization"
      :range="{ min: 0, max: 1, step: 0.01 }"
      disabled
    >
    </base-param-field>
    <base-param-field
      label="Isotope ratio tolerance"
      path="visualization/paramIsotopeRatioTolerance"
      @paramChange="reloadMatches"
      :range="{ min: 0, max: 1, step: 0.1 }"
    >
    </base-param-field>
    <base-param-field
      label="Minimum peak intensity"
      path="visualization/paramPeakMinIntensity"
      @paramChange="reloadVisualization"
      :range="{ min: 0, max: 10000, step: 500 }"
    >
    </base-param-field>
    <base-param-field
      label="Minimum isotope correlation"
      path="visualization/paramMinIsotopeCorrelation"
      @paramChange="reloadMatches"
      :range="{ min: 0, max: 1, step: 0.1 }"
    >
    </base-param-field>
    <base-param-field
      label="Probable match threshold [%]"
      path="visualization/paramProbableMatchThreshold"
      @paramChange="onProbableMatchThresholdChange"
      :range="{ min: 0, max: 1, step: 0.1 }"
      type="is-danger"
    >
    </base-param-field>
    <base-param-field
      label="Possible match threshold [%]"
      path="visualization/paramPossibleMatchThreshold"
      @paramChange="onPossibleMatchThresholdChange"
      :range="{ min: 0, max: 1, step: 0.1 }"
      type="is-warning"
    >
    </base-param-field>
    <div style="display: flex; align-items: center">
      <b-tooltip
        label="Revert changes"
        type="is-info"
        position="is-right"
        animated
      >
        <b-button
          icon-right="undo-variant"
          size="is-small"
          :disabled="!paramsChanged"
          @click="undoChanges"
          style="margin-right: 5px"
        >
        </b-button>
      </b-tooltip>

      <b-tooltip
        label="Set default parameters"
        type="is-info"
        position="is-right"
        animated
      >
        <b-button
          type="is-dark"
          icon-right="file-restore"
          size="is-small"
          :disabled="isDefaultSettings"
          @click="setDefaultFilterParams"
          style="margin-right: 5px"
        >
        </b-button>
      </b-tooltip>

      <b-tooltip
        label="Delete filtering parameters"
        type="is-danger"
        position="is-right"
        animated
      >
        <b-button
          type="is-danger"
          icon-right="delete"
          size="is-small"
          @click="filterParamsDelete"
          :disabled="
            this.ionInFocus.filter_params &&
            this.ionInFocus.instrument in this.ionInFocus.filter_params
              ? false
              : true
          "
        >
        </b-button>
      </b-tooltip>

      <div class="column is-one-half" style="text-align: right">
        <b-button
          type="is-primary"
          icon-left="content-save"
          :loading="isSaving"
          :disabled="!paramsChanged"
          @click="saveFilterSettings"
          >{{ isSaving ? "Please wait..." : "Save filter settings" }}
        </b-button>
      </div>
    </div>
  </section>
</template>

<script>
import BaseParamField from "./BaseParamField.vue";

import { call, get, sync } from "vuex-pathify";

export default {
  name: "ThePaneFilterSettingsIon",
  components: {
    BaseParamField,
  },
  data() {
    return {
      initialParams: {},
      isSaving: false,
    };
  },
  computed: {
    ...sync({
      // filter parameters
      paramMzTolerance: "visualization/paramMzTolerance",
      paramMinIsotopeAbundance: "visualization/paramMinIsotopeAbundance",
      paramPeakMinIntensity: "visualization/paramPeakMinIntensity",
      paramIsotopeRatioTolerance: "visualization/paramIsotopeRatioTolerance",
      paramMinIsotopeCorrelation: "visualization/paramMinIsotopeCorrelation",
      paramProbableMatchThreshold: "visualization/paramProbableMatchThreshold",
      paramPossibleMatchThreshold: "visualization/paramPossibleMatchThreshold",
    }),
    ...get({
      batchActive: "batch/active",
      sampleFocused: "sample/active",
      ionInFocus: "visualization/ionInFocus",
      isotopesInFocus: "visualization/isotopesInFocus",
      defaultFilterParams: "visualization/defaultFilterParams",
    }),
    paramsChanged() {
      // Check if any parameter has changed
      return Object.keys(this.initialParams).some((key) => {
        return this.initialParams[key] !== this[key];
      });
    },
    isDefaultSettings() {
      return Object.keys(this.defaultFilterParams).every((key) => {
        return this[key] === this.defaultFilterParams[key];
      });
    },
  },
  methods: {
    ...call({
      batchLoadBatch: "batch/loadBatch",
      reloadMatchesSample: "sample/loadMatches",
      getSampleIonMatches: "visualization/getSampleIonMatches",
      emitVisualization: "visualization/emitVisualization",
      reloadMatches: "visualization/reloadMatches",
      saveFilterParams: "visualization/saveFilterParams",
      deleteInstrumentFilterParams:
        "visualization/deleteInstrumentFilterParams",
      setDefaultFilterParams: "visualization/setDefaultFilterParams",
    }),
    onProbableMatchThresholdChange() {
      if (this.paramProbableMatchThreshold < this.paramPossibleMatchThreshold) {
        this.paramPossibleMatchThreshold = this.paramProbableMatchThreshold;
      }
      this.reloadMatches();
    },
    onPossibleMatchThresholdChange() {
      if (this.paramProbableMatchThreshold < this.paramPossibleMatchThreshold) {
        this.paramProbableMatchThreshold = this.paramPossibleMatchThreshold;
      }
      this.reloadMatches();
    },

    reloadVisualization() {
      this.emitVisualization({
        sampleId: this.sampleFocused.sample_item_id,
        ionId: this.ionInFocus.target_ion_id,
      });
      this.reloadMatches();
    },
    async saveFilterSettings() {
      this.isSaving = true;
      await this.saveFilterParams();
      this.isSaving = false;
      this.storeInitialParams();
      await this.reloadMatches();
    },
    undoChanges() {
      // Revert filter parameters to their initial values
      Object.keys(this.initialParams).forEach((key) => {
        this[key] = this.initialParams[key];
      });
    },
    filterParamsDelete() {
      this.$buefy.dialog.confirm({
        title: "Deleting filtering parameters",
        message: `Are you sure you want to delete filtering parameters of "${this.ionInFocus.instrument}" instrument for ion "${this.ionInFocus.target_ion_formula}"?`,
        confirmText: "Delete",
        onConfirm: async () => {
          this.setDefaultFilterParams();
          await this.deleteInstrumentFilterParams();
          await this.reloadMatches();
          this.storeInitialParams();
        },
      });
    },
    storeInitialParams() {
      this.initialParams = {
        paramMzTolerance: this.paramMzTolerance,
        paramMinIsotopeAbundance: this.paramMinIsotopeAbundance,
        paramIsotopeRatioTolerance: this.paramIsotopeRatioTolerance,
        paramPeakMinIntensity: this.paramPeakMinIntensity,
        paramMinIsotopeCorrelation: this.paramMinIsotopeCorrelation,
        paramProbableMatchThreshold: this.paramProbableMatchThreshold,
        paramPossibleMatchThreshold: this.paramPossibleMatchThreshold,
      };
    },
  },
  mounted() {
    this.storeInitialParams();
  },
};
</script>
