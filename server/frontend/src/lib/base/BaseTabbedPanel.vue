<script setup>
import Panel from 'primevue/panel'
import Button from 'primevue/button'
import TabMenu from 'primevue/tabmenu'

defineProps({
  label: {
    type: String,
    required: true
  },
  icon: {
    type: String,
    required: true
  },
  contextMenu: {
    type: Object,
    required: false
  },
  pt: {
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
      <TabMenu :model="[{ label, icon }]" />
    </template>
    <template #icons>
      <slot name="menu"></slot>
    </template>
    <slot></slot>
  </Panel>
</template>
