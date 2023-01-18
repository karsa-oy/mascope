<template>
  <section style="padding: 1em">
    <base-param-field
      label="Min. match score"
      path="calibration/paramMatchScoreMin"
      :range="{ min: 0, max: 1, step: .1 }"
      type="is-primary"
    >
    </base-param-field>
    <base-param-field
      label="Refine window [ppm]"
      path="calibration/paramRefineWindow"
      :range="{ min: 0, max: 100, step: 1 }"
      type="is-primary"
    >
    </base-param-field>
    <base-param-field
      label="Min. isotope abundance"
      path="calibration/paramMinIsotopeAbundance"
      :range="{ min: 0, max: 1, step: .1 }"
      type="is-primary"
    >
    </base-param-field>
    <base-param-field
      label="Min. peak intensity"
      path="calibration/paramMinPeakIntensity"
      :range="{ min: 0, max: 100000, step: 1000 }"
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
    }),
  },
  methods: {
    ...call({
    }),
  },
};
</script>