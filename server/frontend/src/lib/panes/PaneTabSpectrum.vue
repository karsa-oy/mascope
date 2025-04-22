<script setup>
import { ref, computed } from 'vue'

import { useWindowSize } from '@vueuse/core'

import Splitter from 'primevue/splitter'
import SplitterPanel from 'primevue/splitterpanel'

import { PaneBrowserPeak, PanePeakAssign } from '@/lib/panes'
import { ChartSampleSpectrum } from '@/lib/charts'

const { height } = useWindowSize()

import { useApp } from '@/stores'

const app = useApp()

const padding = 180

const [initTop, initBottom] = JSON.parse(localStorage.getItem('spectrum-tab-split'))

const topSplit = ref(initTop)
const bottomSplit = ref(initBottom)
const topHeight = computed(() => topSplit.value)
const bottomHeight = computed(() => ((height.value - padding) * bottomSplit.value) / 100 - 50)
</script>

<template>
  <Splitter
    layout="vertical"
    stateStorage="local"
    stateKey="spectrum-tab-split"
    :style="`height: calc(100vh - ${padding}px); width: 100%`"
    @resizeend="
      ({ sizes }) => {
        topSplit = sizes[0]
        bottomSplit = sizes[1]
      }
    "
  >
    <SplitterPanel>
      <ChartSampleSpectrum :height="topHeight" />
    </SplitterPanel>
    <SplitterPanel>
      <div class="row">
        <PaneBrowserPeak :height="bottomHeight" />
        <PanePeakAssign :height="bottomHeight" />
      </div>
    </SplitterPanel>
  </Splitter>
</template>

<style scoped>
.row {
  height: 100%;
  justify-content: space-around;
  gap: 0.5rem;
}
</style>
