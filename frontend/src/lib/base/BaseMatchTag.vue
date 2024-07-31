<script setup>
import { computed } from 'vue'

import Tag from 'primevue/tag'

import { alarmsList } from '@/lib/constants'

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
  }
})

const formatter = new Intl.NumberFormat('en-US', {
  style: 'percent',
  minimumIntegerDigits: 2,
  minimumFractionDigits: 2,
  maximumFractionDigits: 2
})

const score = computed(() =>
  props.row?.match_score != null && !isNaN(props.row?.match_score)
    ? formatter.format(props.row.match_score)
    : null
)

const severity = computed(() => {
  switch (props.row.match_category) {
    case 2:
      return 'danger'
    case 1:
      return 'warn'
    default:
      return 'success'
  }
})

const nonAlarmTarget = computed(
  () =>
    'target_collection_type' in props.row && !alarmsList.includes(props.row.target_collection_type)
)
const zeroScored = computed(() => props.score == '00.00%')
</script>

<template>
  <Tag
    v-if="score"
    :key="score"
    v-tooltip.right="tooltip"
    :value="text ? `Match score: ${score}` : score"
    :severity="severity"
    :class="nonAlarmTarget || zeroScored ? 'pale' : ''"
    :style="style"
  />
</template>

<style>
.pale {
  opacity: 0.5;
}
</style>
