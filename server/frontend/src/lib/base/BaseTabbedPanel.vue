<script setup>
import Panel from 'primevue/panel'
import Button from 'primevue/button'
import ProgressSpinner from 'primevue/progressspinner'

import { BaseStatusIcon } from '@/lib/base'

defineProps({
  label: {
    type: String,
    required: true
  },
  icon: {
    type: String,
    required: true
  },
  clear: {
    type: Function,
    required: false
  },
  loading: {
    type: Boolean,
    required: false,
    default: false
  },
  contextMenu: {
    type: Object,
    required: false
  },
  pt: {
    type: Object,
    required: false
  },
  status: {
    type: Object,
    required: false
  }
})
</script>

<template>
  <Panel
    class="browser"
    style="border: none"
    @contextmenu.prevent.stop="
      (event) => {
        contextMenu?.onClick(event)
      }
    "
    :pt="pt"
  >
    <template #header>
      <div class="label">
        <Button
          v-if="clear"
          v-tooltip.right="'Back to sample batches'"
          icon="pi ph ph-caret-left"
          @click="clear()"
          text
          severity="secondary"
          size="small"
          class="back-button"
        />
        <span :class="icon" />{{ label }}
        <BaseStatusIcon
          v-if="status"
          :status="status.status"
          :config="status.config"
          :onAction="status.onRematch"
        />
      </div>
    </template>
    <template #icons>
      <slot name="menu"></slot>
    </template>
    <slot v-if="!loading"></slot>
    <div v-else class="spinner">
      <div><ProgressSpinner strokeWidth="5px" />loading...</div>
    </div>
  </Panel>
</template>

<style scoped>
.label {
  display: flex;
  flex-flow: row nowrap;
  align-items: center;
  gap: 0.5rem;
  color: var(--p-primary-color);
  font-weight: bold;
  margin: 0.6rem;
  height: 25.15px;
}

.status-button {
  opacity: 0.8;
  margin-left: -0.2rem;
}

.back-button {
  opacity: 0.4;
}

.status-button:hover,
.back-button:hover {
  opacity: 1;
}
</style>
