<script setup>
import { BaseParamField } from '@/lib/base'

const mzCalibrationParams = defineModel('mzCalibrationParams')
</script>

<template>
  <BaseParamField
    label="Min. match score"
    v-model:param="mzCalibrationParams.match_score_min"
    :range="{ min: 0, max: 1, step: 0.1 }"
  />
  <BaseParamField
    label="Refine window [ppm]"
    v-model:param="mzCalibrationParams.refine_window"
    :range="{ min: 0, max: 1000, step: 1 }"
  />
  <BaseParamField
    label="Min. isotope abundance"
    v-model:param="mzCalibrationParams.min_isotope_abundance"
    :range="{ min: 0, max: 1, step: 0.05 }"
  />
  <BaseParamField
    label="Min. peak intensity"
    v-model:param="mzCalibrationParams.peak_intensity_min"
    :range="{ min: 0, max: 100000, step: 1000 }"
  />
</template>
