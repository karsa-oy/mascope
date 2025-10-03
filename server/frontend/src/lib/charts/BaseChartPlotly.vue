<script setup>
import { ref, computed, onMounted, onBeforeUnmount, watchEffect, useSlots } from 'vue'

import Plotly from 'plotly.js-dist-min'

import ProgressSpinner from 'primevue/progressspinner'
import Button from 'primevue/button'
import Popover from 'primevue/popover'

import { useWindowSize } from '@vueuse/core'

import { useApp } from '@/stores'

const win = useWindowSize()

const app = useApp()

const props = defineProps({
  id: {
    type: String,
    required: true
  },
  title: {
    type: String
  },
  subtitle: {
    type: String,
    required: false
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
  },
  loading: {
    type: Boolean,
    default: false
  },
  height: {
    type: Number,
    required: false
  }
})
const slots = useSlots()

const emit = defineEmits(['click', 'dragmode', 'select', 'zoom'])

const plot = ref(null)
const created = ref(false)
const settings = ref()

const resetSelection = () => {
  if (plot.value && props.data.length > 0) {
    // removes the selection
    Plotly.update(plot.value, {}, { selections: [] })
    // removes the selection overlay
    Plotly.restyle(plot.value, { selectedpoints: [null] })
  }
}

// reset chart zoom to autorange
const resetZoom = () => {
  if (plot.value) {
    Plotly.relayout(plot.value, {
      'xaxis.autorange': true,
      'yaxis.autorange': true
    })
  }
}

const selectPoints = (pointIndices) => {
  if (plot.value && props.data.length > 0) {
    // Make the selection
    Plotly.update(plot.value, {}, { selections: pointIndices })
    // Make the selection overlay
    Plotly.restyle(plot.value, { selectedpoints: [pointIndices] })
  }
}

defineExpose({
  resetSelection,
  resetZoom,
  selectPoints
})

const derived = computed(() => ({
  layout: Object.assign(
    {
      ...(!props.hideTitle
        ? {
            title: {
              text: props.subtitle
                ? `${props.title}<br><span style="font-size: 14px; font-weight: 400; opacity: 0.85;">${props.subtitle}</span>`
                : props.title,
              pad: {
                b: 10
              }
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

function handleClick(event) {
  const { data, x, y } = event.points[0]
  emit('click', { data, x, y, event: event.event, ...event.points[0] })
}

function handleSelect(event) {
  if (event && event.points.length === 0) {
    // Skip selection event for programmatically triggered selections
    return
  }
  const pointIndices = event
    ? [...new Set(event.points.map((point) => point.pointIndex))].sort()
    : []
  emit('select', { points: pointIndices })
}

function handleRelayout(data) {
  // Handle zoom events
  const xmin = data['xaxis.range[0]']
  const xmax = data['xaxis.range[1]']
  const ymin = data['yaxis.range[0]']
  const ymax = data['yaxis.range[1]']
  emit('zoom', {
    rangeX: xmin != null && xmax != null ? { range: [xmin, xmax] } : null,
    rangeY: ymin != null && ymax != null ? { range: [ymin, ymax] } : null
  })
  // Handle dragmode changes
  const dragmode = data['dragmode']
  if (dragmode) {
    // Update dragmode state
    emit('dragmode', dragmode)
  }
}

onMounted(() => {
  // create the plot
  Plotly.newPlot(plot.value, props.data, derived.value.layout, derived.value.config)
  // add the event listener
  plot.value.on('plotly_click', handleClick)
  plot.value.on('plotly_relayout', handleRelayout)
  plot.value.on('plotly_selected', handleSelect)
  // mark as created
  created.value = true
})
onBeforeUnmount(() => {
  plot.value?.removeEventListener('plotly_click', handleClick)
  plot.value?.removeEventListener('plotly_relayout', handleRelayout)
  plot.value?.removeEventListener('plotly_selected', handleSelect)
})

const ready = computed(
  () => created.value && props.data && derived.value.layout && app.ui.split.right
)

watchEffect(
  () => {
    if (ready.value) {
      console.log(`📊 [chart] redrawing chart ${props.id} with height ${props.height}`)
      // adapt to changes
      Plotly.react(plot.value, props.data, derived.value.layout, derived.value.config)
      // Relayout to autoranges to fix horizontal-only zoom
      Plotly.relayout(plot.value, {
        'xaxis.autorange': derived.value.layout.xaxis.autorange ? true : false,
        'yaxis.autorange': derived.value.layout.yaxis.autorange ? true : false
      })
    }
  },
  { flush: 'post' }
)
</script>

<template>
  <div style="position: relative; width: 100%; height: 100%" :class="props.loading ? 'faded' : ''">
    <div class="overlay" v-if="props.loading">
      <ProgressSpinner />
    </div>
    <div
      ref="plot"
      :id="id"
      class="plot"
      style="width: 100%; height: 100%"
      :key="`${win.width}-${win.height}-${height}`"
      @contextmenu="
        (e) => {
          e.preventDefault()
        }
      "
    />
    <div class="topleft" v-if="slots.settings">
      <Button
        v-tooltip.right="'Chart settings'"
        severity="secondary"
        text
        @click="
          (event) => {
            settings.toggle(event)
          }
        "
        icon="pi pi-chart-bar"
      />
      <Popover ref="settings">
        <slot name="settings" />
      </Popover>
    </div>
    <div class="bottomleft" v-if="slots.origin">
      <slot name="origin" />
    </div>
  </div>
</template>

<style scoped>
.plot :deep(*) {
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
  fill: var(--p-chip-background) !important;
  opacity: 0.3;
}

.faded {
  opacity: 0.3;
}

.overlay {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  z-index: 100;
  display: grid;
  place-items: center;
}

.topleft {
  position: absolute;
  top: 0;
  left: 0;
  z-index: 50;
}

.bottomleft {
  position: absolute;
  bottom: 0;
  left: 0;
  z-index: 50;
}
</style>
