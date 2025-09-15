<script setup>
import Button from 'primevue/button'
import ProgressSpinner from 'primevue/progressspinner'

defineProps({
  status: {
    type: String,
    required: true
  },
  config: {
    type: Object,
    required: true
  },
  onAction: {
    type: Function,
    default: null
  }
})
</script>

<template>
  <div class="status-icon">
    <Button
      v-if="status in config && config[status].type === 'button'"
      :icon="config[status].icon"
      v-tooltip.right="config[status].tooltip"
      :severity="config[status].severity"
      :disabled="config[status].disabled"
      size="small"
      text
      class="status-button"
      @click="onAction?.()"
    />
    <div
      v-else-if="status in config && config[status].type === 'spinner'"
      v-tooltip.right="config[status].tooltip"
      class="status-spinner"
    >
      <ProgressSpinner style="width: 16px; height: 16px" strokeWidth="3" />
    </div>
  </div>
</template>

<style scoped>
.status-button {
  opacity: 0.8;
  margin-left: -0.2rem;
}

.status-button:hover {
  opacity: 1;
}

.status-spinner {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  margin-left: -0.2rem;
}
</style>
