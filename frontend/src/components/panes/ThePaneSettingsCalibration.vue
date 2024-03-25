<script setup>
import BaseParamField from '@/components/base/BaseParamField.vue'

import { useCalibrationStore } from '@/stores'

const calibrationStore = useCalibrationStore()
</script>

<template>
  <section style="padding: 1em">
    <base-param-field
      label="Min. match score"
      v-model:param="calibrationStore.paramMatchScoreMin"
      :range="{ min: 0, max: 1, step: 0.1 }"
      type="is-primary"
    >
    </base-param-field>
    <base-param-field
      label="Refine window [ppm]"
      v-model:param="calibrationStore.paramRefineWindow"
      :range="{ min: 0, max: 100, step: 1 }"
      type="is-primary"
    >
    </base-param-field>
    <base-param-field
      label="Min. isotope abundance"
      v-model:param="calibrationStore.paramMinIsotopeAbundance"
      :range="{ min: 0, max: 1, step: 0.1 }"
      type="is-primary"
    >
    </base-param-field>
    <base-param-field
      label="Min. peak intensity"
      v-model:param="calibrationStore.paramMinPeakIntensity"
      :range="{ min: 0, max: 100000, step: 1000 }"
      type="is-primary"
    >
    </base-param-field>
  </section>
</template>
