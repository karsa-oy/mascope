<script setup>
import BaseParamField from '@/lib/base/BaseParamField.vue'

import { useMzFit } from '@/stores'

const mzFit = useMzFit()
</script>

<template>
  <BaseParamField
    label="Min. match score"
    v-model:param="mzFit.params.match_score_min"
    :range="{ min: 0, max: 1, step: 0.1 }"
  />
  <BaseParamField
    label="Refine window [ppm]"
    v-model:param="mzFit.params.refine_window"
    :range="{ min: 0, max: 100, step: 1 }"
  />
  <BaseParamField
    label="Min. isotope abundance"
    v-model:param="mzFit.params.min_isotope_abundance"
    :range="{ min: 0, max: 1, step: 0.1 }"
  />
  <BaseParamField
    label="Min. peak intensity"
    v-model:param="mzFit.params.peak_intensity_min"
    :range="{ min: 0, max: 100000, step: 1000 }"
  />
</template>
