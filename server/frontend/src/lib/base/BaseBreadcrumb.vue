<script setup>
import { ref } from 'vue'
import Button from 'primevue/button'
import ContextMenu from 'primevue/contextmenu'

defineProps({
  items: {
    type: Array,
    required: true
    // Each item: { icon, label?, action?, tooltip?, contextMenu?, disabled? }
  }
})

const contextMenuRefs = ref({})
</script>

<template>
  <menu class="breadcrumb">
    <template v-for="(item, index) in items" :key="index">
      <Button
        :icon="item.icon"
        :label="item.label"
        v-tooltip.right="item.tooltip"
        severity="secondary"
        text
        size="small"
        :disabled="item.disabled"
        @click="item.action?.()"
        @contextmenu.prevent.stop="
          (event) => {
            if (item.contextMenu && item.contextMenuHandler) {
              item.contextMenuHandler(event)
            }
          }
        "
        :class="{ 'breadcrumb-current': !item.action }"
      />
      <span v-if="index < items.length - 1" class="pi ph ph-caret-right breadcrumb-separator" />

      <!-- Context menu for this breadcrumb item -->
      <ContextMenu
        v-if="item.contextMenu"
        :ref="(el) => (contextMenuRefs[index] = el)"
        :model="item.contextMenu.items"
        appendTo="self"
      />
    </template>
  </menu>
</template>

<style scoped>
.breadcrumb {
  display: flex;
  flex-flow: row nowrap;
  align-items: center;
  gap: 0.3rem;
  padding: 0;
  margin: 0.3rem 0.6rem;
  height: 25.15px;
}

.breadcrumb .p-button {
  padding: 0.1rem 0.5rem;
  border-radius: 1rem;
  color: var(--p-primary-color);
  font-weight: 500;
}

.breadcrumb .p-button:first-child {
  padding: 0.1rem;
}

.breadcrumb-current {
  font-weight: bold;
  cursor: default;
  opacity: 1 !important;
}

.breadcrumb .p-button:disabled {
  opacity: 0.6;
  cursor: default;
}

.breadcrumb-separator {
  opacity: 0.5;
  font-size: 0.9rem;
}
</style>
