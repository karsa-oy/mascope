<script setup>
import { ref } from 'vue'

import { PaneBrowserPeak, PanePeakAssign } from '@/lib/panes'
import { ChartSampleSpectrum } from '@/lib/charts'

import { useApp } from '@/stores'

const app = useApp()
</script>

<template>
  <div class="col" :style="`calc(${app.ui.split.right}vw - 4rem)`">
    <div>
      <ChartSampleSpectrum />
    </div>
    <div class="row">
      <PaneBrowserPeak />
      <PanePeakAssign />
    </div>
  </div>
</template>

<style scoped>
div {
  gap: 0.5rem;
}
.col {
  width: 100%;
  align-items: stretch;
}
.row {
  align-items: stretch;
  height: 400px;
  justify-content: space-around;
}
</style>
