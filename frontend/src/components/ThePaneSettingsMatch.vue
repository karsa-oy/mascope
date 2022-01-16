<template>
  <section style="padding: 1em">
    <h2 class="subtitle">Matching</h2>
    <base-param-field
      label="m/z tolerance [ppm]"
      path="workspace/match/paramMzTolerance"
      :range="{ min: 0, max: 1000, step: 1 }"
    >
    </base-param-field>
    <base-param-field
      label="Isotope ratio tolerance [%]"
      path="workspace/match/paramIsoRatioTolerance"
      :range="{ min: 0, max: 20, step: 0.05 }"
    >
    </base-param-field>
    <base-param-field
      label="Probable match threshold [%]"
      path="workspace/match/paramProbableMatchThreshold"
      :range="{ min: paramPossibleMatchThreshold, max: 1, step: 0.005 }"
      type="is-success"
    >
    </base-param-field>
    <base-param-field
      label="Possible match threshold [%]"
      path="workspace/match/paramPossibleMatchThreshold"
      :range="{ min: 0, max: paramProbableMatchThreshold, step: 0.005 }"
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
      paramPossibleMatchThreshold:
        "workspace/match/paramPossibleMatchThreshold",
      paramProbableMatchThreshold:
        "workspace/match/paramProbableMatchThreshold",
    }),
  },
};
</script>