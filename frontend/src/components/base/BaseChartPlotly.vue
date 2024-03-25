<script setup>
import { ref, computed, onMounted } from 'vue'
import Plotly from './external/Plotly.vue'

defineOptions({
  inheritAttrs: false
})

const props = defineProps({
  id: {
    type: String,
    required: true
  },
  title: {
    type: String
  },
  config: {
    type: Object
  },
  data: {
    type: Array
  },
  layout: {
    type: Object
  }
})

const plotlyChart = ref(null)

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

onMounted(() => {
  plotlyChart.value?.addEventListener('contextmenu', (event) => {
    event.preventDefault()
  })
})
</script>

<template>
  <section ref="plotlyChart">
    <plotly
      :id="id"
      :data="data"
      :layout="{ ...baseLayout, ...layout }"
      style="width: 100%; height: 100%"
      v-bind="{ ...baseConfig, ...config }"
      v-on="$attrs"
    ></plotly>
  </section>
</template>
