<template>
  <section style="padding: 1em">
    <h2 class="subtitle">Matching</h2>
    <base-param-field
      label="m/z tolerance [ppm]"
      path="match/param/mzTolerance"
      :range="{ min: 0, max: 1000, step: 1 }"
    >
    </base-param-field>
    <base-param-field
      label="Isotope ratio tolerance [%]"
      path="match/param/isoRatioTolerance"
      :range="{ min: 0, max: 20, step: 1 }"
    >
    </base-param-field>
    <base-param-field
      label="Minimum peak intensity"
      path="match/param/peakMinIntensity"
      :range="{ min: 0, max: 10000, step: 1 }"
    >
    </base-param-field>
    <base-param-field
      label="Minimum peak separation"
      path="match/param/peakMinSeparation"
      :range="{ min: 0, max: 100, step: 1 }"
    >
    </base-param-field>
    <base-param-field
      label="Probable match threshold [%]"
      path="match/param/probableMatchThreshold"
      :range="{ min: paramPossibleMatchThreshold, max: 1, step: 0.1 }"
      type="is-success"
    >
    </base-param-field>
    <base-param-field
      label="Possible match threshold [%]"
      path="match/param/possibleMatchThreshold"
      :range="{ min: 0, max: paramProbableMatchThreshold, step: 0.1 }"
      type="is-primary"
    >
    </base-param-field>
  </section>
</template>


<script>
import BaseParamField from "./BaseParamField.vue";

import { bindState } from "$lib/store";

export default {
  name: "ThePaneSettingsMatch",
  components: {
    BaseParamField,
  },
  computed: {
    ...bindState({
      paramPossibleMatchThreshold: "match/param/possibleMatchThreshold",
      paramProbableMatchThreshold: "match/param/probableMatchThreshold",
    }),
  },
};
</script>