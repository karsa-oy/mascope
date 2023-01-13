<template>
  <section style="padding: 1em">
    <h2 class="subtitle">Batch parameters</h2>
    <base-param-field
      label="m/z tolerance [ppm]"
      path="batch/paramMzTolerance"
      @paramChange="reloadMatches"
      :range="{ min: 0, max: 100, step: 1 }"
    >
    </base-param-field>
    <base-param-field
      label="Minimum isotope abundance"
      path="batch/paramMinIsotopeAbundance"
      @paramChange="reloadMatches"
      :range="{ min: 0, max: 1, step: .01 }"
    >
    </base-param-field>
    <base-param-field
      label="Isotope ratio tolerance"
      path="batch/paramIsotopeRatioTolerance"
      @paramChange="reloadMatches"
      :range="{ min: 0, max: 1, step: .01 }"
      disabled
    >
    </base-param-field>
    <base-param-field
      label="Minimum peak intensity"
      path="batch/paramPeakMinIntensity"
      @paramChange="reloadMatches"
      :range="{ min: 0, max: 10000, step: 1 }"
    >
    </base-param-field>
    <base-param-field
      label="Minimum peak separation"
      path="batch/paramPeakMinSeparation"
      @paramChange="reloadMatches"
      :range="{ min: 0, max: 100, step: 1 }"
      disabled
    >
    </base-param-field>
    <base-param-field
      label="Probable match threshold [%]"
      path="batch/paramProbableMatchThreshold"
      @paramChange="reloadMatches"
      :range="{ min: paramPossibleMatchThreshold, max: 1, step: 0.1 }"
      type="is-danger"
    >
    </base-param-field>
    <base-param-field
      label="Possible match threshold [%]"
      path="batch/paramPossibleMatchThreshold"
      @paramChange="reloadMatches"
      :range="{ min: 0, max: paramProbableMatchThreshold, step: 0.1 }"
      type="is-primary"
    >
    </base-param-field>
  </section>
</template>


<script>
import BaseParamField from "./BaseParamField.vue";

import { call, get } from "vuex-pathify";

export default {
  name: "ThePaneSettingsMatch",
  components: {
    BaseParamField,
  },
  computed: {
    ...get({
      batchActive: "batch/active",
      paramPossibleMatchThreshold: "batch/paramPossibleMatchThreshold",
      paramProbableMatchThreshold: "batch/paramProbableMatchThreshold",
      sampleFocused: "sample/active",
    }),
  },
  methods: {
    ...call({
      reloadMatchesBatch: "batch/loadSamples",
      reloadMatchesSample: "sample/loadMatches",
    }),
    reloadMatches() {
      if (!this.batchActive) return;
      this.reloadMatchesBatch();
      if (this.sampleFocused) this.reloadMatchesSample();
    },
  },
};
</script>