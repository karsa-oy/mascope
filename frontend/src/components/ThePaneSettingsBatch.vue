<template>
  <section style="padding: 1em">
    <h2 class="subtitle">Batch parameters</h2>
    <base-param-field
      label="m/z tolerance [ppm]"
      path="batch/active@filter_params.mz_tolerance"
      @paramChange="reloadMatches"
      :range="{ min: 0, max: 1000, step: 1 }"
    >
    </base-param-field>
    <base-param-field
      label="Minimum isotope abundance"
      path="batch/active@filter_params.min_isotope_abundance"
      @paramChange="reloadMatches"
      :range="{ min: 0, max: 1, step: .01 }"
    >
    </base-param-field>
    <base-param-field
      label="Isotope ratio tolerance"
      path="batch/active@filter_params.isotope_ratio_tolerance"
      @paramChange="reloadMatches"
      :range="{ min: 0, max: 1, step: .01 }"
    >
    </base-param-field>
    <base-param-field
      label="Minimum peak intensity"
      path="batch/active@filter_params.peak_min_intensity"
      @paramChange="reloadMatches"
      :range="{ min: 0, max: 10000, step: 1 }"
    >
    </base-param-field>
    <base-param-field
      label="Minimum peak separation"
      path="batch/active@filter_params.peak_min_separation"
      @paramChange="reloadMatches"
      :range="{ min: 0, max: 100, step: 1 }"
      disabled
    >
    </base-param-field>
    <base-param-field
      label="Probable match threshold [%]"
      path="batch/active@filter_params.probable_match_threshold"
      :range="{ min: paramPossibleMatchThreshold, max: 1, step: 0.1 }"
      type="is-success"
    >
    </base-param-field>
    <base-param-field
      label="Possible match threshold [%]"
      path="batch/active@filter_params.possible_match_threshold"
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
      paramPossibleMatchThreshold: "batch/active@filter_params.possible_match_threshold",
      paramProbableMatchThreshold: "batch/active@filter_params.probable_match_threshold",
      sampleFocused: "sample/active",
    }),
  },
  methods: {
    ...call({
      reloadMatchesBatch: "batch/loadSamples",
      reloadMatchesSample: "sample/loadMatches",
    }),
    reloadMatches() {
      this.reloadMatchesBatch();
      if (this.sampleFocused) this.reloadMatchesSample();
    },
  },
};
</script>