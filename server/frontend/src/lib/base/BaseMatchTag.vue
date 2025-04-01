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

const alarmMode = computed(() => {
  //  Check if the target_collection_type is in alarmsList, relevent for target browser match tags.
  const targetCollectionType = alarmsList.includes(props.row.target_collection_type)
  // Check if any match_collection_types are in alarmsList, relevent for sample browser match tags.
  const matchCollectionTypes = props.row.match_collection_types?.some((type) =>
    alarmsList.includes(type)
  )

  return targetCollectionType || matchCollectionTypes
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
    :class="nofade || alarmMode || zeroScored ? '' : 'pale'"
    :style="style"
  />
</template>

<style>
.pale {
  opacity: 0.5;
}
</style>
