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
const tooltipActive = computed(() => {
  return Object.keys(props.tooltip).length > 0
})

function clicked() {
  emit('tagClicked', props.row)
}
</script>

<template>
  <b-field>
    <b-tooltip
      :active="tooltipActive"
      :delay="200"
      position="is-left"
      type="is-white"
      append-to-body
      size="is-small"
      multilined
    >
      <b-tag
        v-if="!(matchScore === null || isNaN(matchScore))"
        :icon="tag.icon"
        :class="tag.class"
        style="font-size: small"
        @click="clicked"
      >
        <span v-if="displayMatchScore" :style="tag.weight">
          {{ formatter.format(matchScore) }}
        </span>
      </b-tag>
      <!-- tooltip slot -->
      <template v-slot:content>
        <template v-for="(value, field) in tooltip" :key="field">
          {{ field }}: {{ value }}<br />
        </template>
      </template>
    </b-tooltip>
  </b-field>
</template>
