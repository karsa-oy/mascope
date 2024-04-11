<script setup>
import { computed } from 'vue'

const props = defineProps({
  displayMatchScore: {
    type: Boolean,
    required: false,
    default: true
  },
  row: {
    type: Object,
    required: false
  },
  tooltip: {
    type: Object,
    required: false
  }
})

const emit = defineEmits(['tagClicked'])

const formatter = new Intl.NumberFormat('en-US', {
  style: 'percent',
  minimumIntegerDigits: 2,
  minimumFractionDigits: 2,
  maximumFractionDigits: 2
})

const matchScore = computed(() =>
  props.row !== null
    ? props.row.matched === undefined || props.row.matched
      ? props.row.match_score
      : null
    : null
)
const tag = computed(() => {
  if (props.row.alarm_mode) {
    switch (props.row.match_category) {
      case 2:
        return {
          category: 'probable',
          class: 'is-danger'
          // weight: "font-weight: bold",
        }
      case 1:
        return {
          category: 'possible',
          class: 'is-warning'
          // weight: "font-weight: bold",
        }
      default:
        return {
          category: 'improbable',
          class: 'is-success'
          // weight: "font-weight: bold",
        }
    }
  } else {
    switch (props.row.match_category) {
      case 2:
        return {
          category: 'probable',
          class: 'is-danger-pale'
        }
      case 1:
        return {
          category: 'possible',
          class: 'is-warning-pale'
        }
      default:
        return {
          category: 'improbable',
          class: 'is-success-pale'
        }
    }
  }
})

const tooltip = computed(() =>
  props.tooltip
    ? Object.entries(props.tooltip)
        .map(([field, value]) => `${field}: ${value}`)
        .join('\n')
    : 'no peaks'
)

function clicked() {
  emit('tagClicked', props.row)
}
</script>

<template>
  <b-field>
    <b-tag
      v-if="!(matchScore === null || isNaN(matchScore))"
      :icon="tag.icon"
      :class="tag.class"
      style="font-size: small"
      @click="clicked"
      v-tooltip.left="tooltip"
    >
      <span v-if="displayMatchScore" :style="tag.weight">
        {{ formatter.format(matchScore) }}
      </span>
    </b-tag>
  </b-field>
</template>

<style>
.p-tooltip {
  font-size: smaller;
}
</style>
