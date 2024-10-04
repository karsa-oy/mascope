<script setup>
import Button from 'primevue/button'

const { field } = defineProps({
  field: {
    required: true
  }
})

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
    <span>{{ field }}</span>
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
