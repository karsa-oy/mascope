<template>
  <section style="padding: 1em">
    <h2 class="subtitle">Targets</h2>
    <base-param-field
      label="Minimum isotope abundance [%]"
      path="workspace/target/paramMinIsoAbu"
      :range="{ min: 0, max: 20, step: 0.05 }"
    >
    </base-param-field>
    <b-field label="Default ionization mechanisms">
      <b-taginput
        v-model="defaultIonMechs"
        ellipsis
        icon="label"
        placeholder="Add ionization mechanisms"
        aria-close-label="Delete ionization mechanism"
      >
      </b-taginput>
    </b-field>
  </section>
</template>


<script>
import BaseParamField from "./BaseParamField.vue";

import { bindState } from "$lib/store";

export default {
  name: "ThePaneSettingsTarget",
  components: {
    BaseParamField,
  },
  computed: {
    ...bindState({
      defaultIonMechs: "workspace/target/defaultIonMechs",
    }),
  },
};
</script>