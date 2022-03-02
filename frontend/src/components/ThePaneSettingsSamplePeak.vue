<template>
  <section style="padding: 1em">
    <h2 class="subtitle">Peak identification</h2>
    <base-param-field
      label="Peak intensity threshold [%]"
      path="workspace/sample/paramPeakMinIntensity"
      :range="{ min: 0, max: 20, step: 0.05 }"
    >
    </base-param-field>
    <base-param-field
      label="Minimum peak seperation [m/z]"
      path="workspace/sample/paramPeakMinSeperation"
      :range="{ min: 0, max: 30, step: 0.05 }"
    >
    </base-param-field>
    <base-param-field
      label="Minimum peak width [m/z]"
      path="workspace/sample/paramPeakMinWidth"
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