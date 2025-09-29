<script setup>
import { computed } from 'vue'

import Tag from 'primevue/tag'

const props = defineProps({
  row: {
    type: Object,
    required: true
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
  const notNull = (props.row?.match?.match_score ?? null) !== null
  const notNaN = !isNaN(props.row?.match?.match_score)
  return notNull && notNaN ? formatter.format(props.row.match?.match_score) : null
})

const severity = computed(() => {
  switch (props.row.match.match_category) {
    case 2:
      return 'danger'
    case 1:
      return 'warn'
    default:
      return 'success'
  }
})

const zeroScored = computed(() => props.score == '00.00%')
</script>

<template>
  <Tag
    v-if="score"
    :key="score"
    v-tooltip.right="tooltip"
    :value="text ? `Match score: ${score}` : score"
    :severity="severity"
    :class="nofade || row.match?.alarming || zeroScored ? '' : 'pale'"
    :style="style"
  />
</template>

<style>
.pale {
  opacity: 0.5;
}
</style>
