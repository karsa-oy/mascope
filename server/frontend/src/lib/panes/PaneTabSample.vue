<script setup>
import { ref, computed } from 'vue'

import { useWindowSize } from '@vueuse/core'

import Splitter from 'primevue/splitter'
import SplitterPanel from 'primevue/splitterpanel'

import { PanePeakAssign } from '@/lib/panes'
import { ChartSampleSpectrum, ChartAssignmentTimeseries } from '@/lib/charts'

const { height } = useWindowSize()

const padding = 180

const storedState = localStorage.getItem('sample-tab-split')
const [initTop, initBottom] = JSON.parse(storedState ?? '[55, 45]')

const topSplit = ref(initTop)
const bottomSplit = ref(initBottom)

// Pixel heights of the two rows, used to nudge the Plotly charts to resize when
// the splitter moves. The top row is split horizontally (inspector | spectrum);
// the bottom row (time series) spans both.
const topHeight = computed(() => ((height.value - padding) * topSplit.value) / 100)
const bottomHeight = computed(() => ((height.value - padding) * bottomSplit.value) / 100)
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
      <SplitterPanel :size="55">
        <Splitter class="top-splitter">
          <SplitterPanel :size="42" class="inspector-panel">
            <PanePeakAssign :height="topHeight - 3" />
          </SplitterPanel>
          <SplitterPanel :size="58">
            <ChartSampleSpectrum :height="topHeight" />
          </SplitterPanel>
        </Splitter>
      </SplitterPanel>
      <SplitterPanel :size="45">
        <ChartAssignmentTimeseries :height="bottomHeight" />
      </SplitterPanel>
    </Splitter>
  </div>
</template>

<style scoped>
.sample-splitter {
  height: 100%;
  width: 100%;
}

.top-splitter {
  height: 100%;
  width: 100%;
  border: none;
}

/* The inspector column scrolls on its own when the assignment card is tall,
   so it never pushes the spectrum out of the top row. */
.inspector-panel {
  overflow-y: auto;
  overflow-x: hidden;
}
</style>
