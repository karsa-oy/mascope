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

const storedState = localStorage.getItem('sample-tab-split')
const [initTop, initBottom] = JSON.parse(storedState ?? '[50, 50]')

const topSplit = ref(initTop)
const bottomSplit = ref(initBottom)
const topHeight = computed(() => topSplit.value)
const bottomHeight = computed(() => ((height.value - padding) * bottomSplit.value) / 100 - 50)
</script>

<template>
  <div class="pane-wrapper">
    <Splitter
      layout="vertical"
      stateStorage="local"
      stateKey="sample-tab-split"
      class="sample-splitter"
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
          <PaneBrowserPeak :height="bottomHeight - 3" />
          <PanePeakAssign :height="bottomHeight - 3" />
        </div>
      </SplitterPanel>
    </Splitter>
  </div>
</template>

<style scoped>
.sample-splitter {
  height: 100%;
  width: 100%;
}

.row {
  display: flex;
  flex-flow: row wrap;
  height: 100%;
  width: 100%;
  max-width: 100%;
  justify-content: flex-start;
  gap: 0.5rem;
  overflow-x: hidden;
  overflow-y: auto;
}

.row > :deep(*) {
  flex: 1 1 300px;
  min-width: 0;
  max-width: 100%;
}
</style>
