<script setup>
import { computed } from 'vue'

import Tag from 'primevue/tag'

const props = defineProps({
  matchScore: {
    type: Number,
    default: null
  },
  matchCategory: {
    type: Number,
    default: 0
  },
  alarming: {
    type: Boolean,
    default: false
  },
  tooltip: {
    type: String
  },
  text: {
    type: Boolean,
    default: false
  },
  style: {
    type: String,
    default: 'font-size: 11px'
  },
  nofade: {
    type: Boolean,
    default: false
  }
})

const formatter = new Intl.NumberFormat('en-US', {
  style: 'percent',
  minimumIntegerDigits: 2,
  minimumFractionDigits: 2,
  maximumFractionDigits: 2
})

const score = computed(() => {
  const notNull = props.matchScore !== null
  const notNaN = !isNaN(props.matchScore)
  return notNull && notNaN ? formatter.format(props.matchScore) : null
})

const severity = computed(() => {
  switch (props.matchCategory) {
    case 2:
      return 'danger'
    case 1:
      return 'warn'
    default:
      return 'success'
  }
})
</script>

<template>
  <Tag
    v-if="score"
    :key="score"
    v-tooltip.right="tooltip"
    :value="text ? `Match score: ${score}` : score"
    :severity="severity"
    :class="nofade || alarming ? '' : 'pale'"
    :style="style"
  />
</template>

<style>
.pale {
  opacity: 0.5;
}
</style>
