<template>
  <section style="padding: 1em">
    <h2 class="subtitle">Peak identification</h2>
    <base-param-field
      label="Peak intensity threshold [%]"
      path="sample/paramPeakMinIntensity"
      :range="{ min: 0, max: 1000, step: 1 }"
    >
    </base-param-field>
    <base-param-field
      label="Minimum peak separation [m/z]"
      path="sample/paramPeakMinSeparation"
      :range="{ min: 0, max: 30, step: 0.05 }"
    >
    </base-param-field>
  </section>
</template>


<script>
import BaseParamField from "./BaseParamField.vue";

export default {
  components: { BaseParamField },
  name: "ThePaneSettingsSamplePeak",
};
</script>