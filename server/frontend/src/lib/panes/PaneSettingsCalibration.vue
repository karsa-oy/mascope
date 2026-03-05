<script setup>
import { BaseParamField } from '@/lib/base'

const mzCalibrationParams = defineModel('mzCalibrationParams')
</script>

<template>
  <div class="calibration-fields">
    <BaseParamField
      label="Min. match score"
      v-model:param="mzCalibrationParams.match_score_min"
      :range="{ min: 0, max: 1, step: 0.1 }"
      :small="true"
    />
    <BaseParamField
      label="Refine window [ppm]"
      v-model:param="mzCalibrationParams.refine_window"
      :range="{ min: 0, max: 1000, step: 1 }"
      :small="true"
    />
    <BaseParamField
      label="Min. isotope abundance"
      v-model:param="mzCalibrationParams.isotope_abundance_min"
      :range="{ min: 0, max: 1, step: 0.05 }"
      :small="true"
    />
    <BaseParamField
      label="Min. peak intensity"
      v-model:param="mzCalibrationParams.peak_intensity_min"
      :range="{ min: 0, max: 100000, step: 1000 }"
      :small="true"
    />
    <BaseParamField
      label="Min. signal-to-noise ratio"
      v-model:param="mzCalibrationParams.snr_threshold"
      :range="{ min: 0, max: 1000, step: 10 }"
      :small="true"
    />
  </div>
</template>


<style scoped>
.calibration-fields {
  display: grid;
  row-gap: 0rem;
}

.calibration-fields > * {
  margin-block: 0 !important;
  padding-block: 0 !important;
}

.calibration-fields :deep(.p-field),
.calibration-fields :deep(.field),
.calibration-fields :deep(.form-row),
.calibration-fields :deep(.param-field),
.calibration-fields :deep(.p-formgrid) {
  margin-block: 0 !important;
  padding-block: 0 !important;
}

.calibration-fields :deep(label) {
  margin-bottom: 0.0rem !important;
}
</style>