<template>
  <section style="padding: 1em">
    <h2 class="subtitle">Targets</h2>
    <base-param-field
      label="Minimum isotope abundance [%]"
      path="target/param/minIsoAbu"
      :range="{ min: 0, max: 100, step: 1 }"
    >
    </base-param-field>
    <b-field label="Ionization mechanisms">
      <base-browser
        name="Ionization mechanisms"
        :levels="ionMechanismLevels"
        >
      </base-browser>
    </b-field>
  </section>
</template>


<script>
import { mapActions } from "vuex";
import { bindState } from "$lib/store";

import BaseBrowser from "./BaseBrowser.vue";
import BaseParamField from "./BaseParamField.vue";

export default {
  name: "ThePaneSettingsTarget",
  components: {
    BaseBrowser, BaseParamField
  },
  computed: {
    ...bindState({
      ionMechanisms: "config/ion_mechanism/rows",
    }),
    ionMechanismLevels() {
      return [{
        rows: this.ionMechanisms,
        cols: [
          {'field': 'mechanism', 'label': 'Mechanism'},
          {'field': 'polarity', 'label': 'Polarity'},
          {'field': 'reagent', 'label': 'Reagent'}
          ],
        rowClick: this.ionMechanismToggle,
      }];
    },
  },
  methods: {
    ...mapActions({
      ionMechanismToggle: "config/ion_mechanism/toggle",
    }),
  },
};
</script>