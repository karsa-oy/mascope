<script setup>
import { ref, computed, onMounted, watchEffect } from 'vue'
import * as Plotly from 'plotly.js-basic-dist'

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
  }
})

const emit = defineEmits('click')

const plot = ref(null)
const ready = ref(false)

const baseConfig = ref({
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
})

const baseLayout = computed(() => ({
  title: {
    text: props.title
  },
  font: {
    color: '#fff'
  },
  hoverinfo: 'name+y',
  plot_bgcolor: '#313239f0',
  paper_bgcolor: 'transparent',
  autosize: true,
  useResizeHandler: true,
  modebar: {
    bgcolor: 'transparent'
  }
}))

function setGraph() {
  if (!ready.value || !plot.value || !props.data || !props.layout) return
  Plotly.newPlot(
    plot.value,
    props.data,
    { ...baseLayout.value, ...props.layout },
    { ...baseConfig.value, ...props.config }
  )
  // event listener
  plot.value.on('plotly_click', (e) => emit('click', e))
}

onMounted(() => {
  ready.value = true
  setGraph()
})

watchEffect(() => {
  setGraph()
})
</script>

<template>
  <div ref="plot" @click.prevent style="width: 100%; height: 100%" />
</template>
