<template>
  <section style="padding: 1em">
    <h2 class="subtitle">Targets</h2>
    <base-param-field
      label="Minimum isotope abundance [%]"
      path="target/param/minIsoAbu"
      :range="{ min: 0, max: 100, step: 0.05 }"
    >
    </base-param-field>
  </section>
</template>


<script>
import BaseParamField from "./BaseParamField.vue";

export default {
  name: "ThePaneSettingsTarget",
  components: {
    BaseParamField,
  },
};
</script>