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
  }
})

const formatter = new Intl.NumberFormat('en-US', {
  style: 'percent',
  minimumIntegerDigits: 2,
  minimumFractionDigits: 2,
  maximumFractionDigits: 2
})

const score = computed(() =>
  props.row?.match_score && !isNaN(props.row?.match_score)
    ? formatter.format(props.row.match_score)
    : formatter.format(0)
)

const severity = computed(() => {
  switch (props.row.match_category) {
    case 2:
      return 'danger'
    case 1:
      return 'warning'
    default:
      return 'success'
  }
})
</script>

<template>
  <Tag
    v-if="row?.match_score !== null"
    :key="score"
    v-tooltip.right="tooltip"
    :value="text ? `Match score: ${score}` : score"
    :severity="severity"
    :class="!row.alarm_mode || score == '00.00%' ? 'pale' : ''"
    style="font-size: 11px"
  />
</template>

<style>
.pale {
  opacity: 0.5;
}
</style>
