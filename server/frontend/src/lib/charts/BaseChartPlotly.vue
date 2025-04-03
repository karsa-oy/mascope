<script setup>
import { ref, computed, onMounted, watchEffect, watch } from 'vue'

import * as Plotly from 'plotly.js-basic-dist'

import { useWindowSize } from '@vueuse/core'

import { useApp } from '@/stores'

const { width, height } = useWindowSize()

const app = useApp()

const props = defineProps({
  id: {
    type: String,
    required: true
  },
  title: {
    type: String
  },
  data: {
    type: Array
  },
  config: {
    type: Object
  },
  layout: {
    type: Object
  },
  hideTitle: {
    type: Boolean,
    default: false
  }
})

const emit = defineEmits('click')

const plot = ref(null)
const created = ref(false)

// reset chart zoom to autorange
const resetZoom = () => {
  if (plot.value) {
    Plotly.relayout(plot.value, {
      'xaxis.autorange': true,
      'yaxis.autorange': true
    })
  }
}
defineExpose({
  resetZoom
})

const derived = computed(() => ({
  layout: Object.assign(
    {
      ...(!props.hideTitle
        ? {
            title: {
              text: props.title
            }
          }
        : {
            margin: {
              t: 40
            },
            title: {
              automargin: false
            }
          }),
      hoverinfo: 'name+y',
      paper_bgcolor: 'transparent',
      autosize: true,
      useResizeHandler: true,
      modebar: {
        bgcolor: 'transparent'
      }
    },
    props.layout
  ),
  config: Object.assign(
    {
      displaylogo: false,
      displayModeBar: true,
      responsive: true,
      modeBarButtonsToRemove: ['autoScale', 'resetScale2d', 'pan2d', 'zoomIn2d', 'zoomOut2d'],
      toImageButtonOptions: {
        format: 'png', // one of png, svg, jpeg, webp
        filename: props.title.toLowerCase().replaceAll(/[\s-]/g, '_'),
        height: 500,
        width: 700,
        scale: 1 // Multiply title/legend/axis/canvas sizes by this factor
      }
    },
    props.config
  )
}))

onMounted(() => {
  Plotly.newPlot(plot.value, props.data, derived.value.layout, derived.value.config)
  // event listener
  plot.value.on('plotly_click', (e) => emit('click', e))
  created.value = true
  Plotly.react(plot.value, props.data, derived.value.layout, derived.value.config)
})

const ready = computed(
  () => created.value && props.data && derived.value.layout && app.ui.split.right
)

watchEffect(
  () => {
    if (ready.value) {
      Plotly.react(plot.value, props.data, derived.value.layout, derived.value.config)
    }
  },
  { flush: 'post' }
)
</script>

<template>
  <div
    ref="plot"
    :id="id"
    class="plot"
    @click.prevent
    style="width: 100%; height: 100%"
    :key="`${width}-${height}`"
  />
</template>

<style scoped>
div {
  max-width: 95%;
}

:deep(*) {
  font-family: Inter !important;
}
:deep(.legendtext),
:deep(.icon) > path,
:deep(.gtitle),
:deep(.xtitle),
:deep(.ytitle),
:deep(.ytick) > text,
:deep(.xtick) > text,
:deep(.annotation-text) {
  fill: var(--p-panel-color) !important;
  color: var(--p-panel-color) !important;
}

:deep(.bg) {
  fill: var(--p-togglebutton-background) !important;
}
</style>
