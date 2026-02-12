<script setup>
import { computed } from 'vue'
import Button from 'primevue/button'

const { field, tooltip } = defineProps({
  field: {
    required: true
  },
  tooltip: {
    type: [String, Object],
    default: null
  }
})

const tooltipConfig = computed(() => {
  if (!tooltip) return null
  if (typeof tooltip === 'string') {
    return { value: tooltip, position: 'top' }
  }
  return tooltip
})

const emit = defineEmits(['copy'])

async function copyField(text) {
  try {
    await navigator.clipboard.writeText(text)
  } catch (err) {
    console.warn(err)
  }
}
</script>

<template>
  <span class="field">
    <span v-tooltip="tooltipConfig">{{ field }}</span>
    <Button
      v-if="field && String(field).length > 0"
      v-tooltip.bottom="{ value: 'Copy to clipboard', showDelay: 2000 }"
      icon="pi pi-clone"
      severity="secondary"
      text
      size="small"
      @click="
        (event) => {
          event.stopPropagation()
          copyField(field)
          emit('copy')
        }
      "
    />
    <slot></slot>
  </span>
</template>

<style scoped>
.field {
  display: flex;
  flex-flow: row;
  align-items: center;
}

.field > :deep(button) {
  visibility: hidden;
}

.field:hover > :deep(button) {
  visibility: visible;
}

:deep(button) {
  width: min-content;
  margin-left: 0.5rem;
  padding: 5px 7px;
}
</style>
