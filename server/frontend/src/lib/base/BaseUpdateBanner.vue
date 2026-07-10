<script setup>
import { ref } from 'vue'

import Button from 'primevue/button'

import { useUpdate } from '@/lib/update'

// A non-blocking notice that a newer build is available. Reloading is cheap
// because the UI restores its location on load, so the user can reload at a
// moment that suits them rather than being interrupted.
const update = useUpdate()
const dismissed = ref(false)
</script>

<template>
  <div v-if="update.available && !dismissed" class="update-banner" role="status">
    <span class="ph ph-arrow-clockwise" />
    <span class="text">A new version of Mascope is available.</span>
    <Button size="small" label="Reload" @click="update.reload()" />
    <Button
      size="small"
      text
      rounded
      aria-label="Dismiss"
      icon="ph ph-x"
      @click="dismissed = true"
    />
  </div>
</template>

<style scoped>
.update-banner {
  position: fixed;
  top: 1rem;
  left: 50%;
  transform: translateX(-50%);
  z-index: 9998;
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 0.5rem 0.5rem 0.5rem 1rem;
  border-radius: 999px;
  background: var(--p-primary-color, #10b981);
  color: var(--p-primary-contrast-color, #fff);
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.2);
}
.update-banner .text {
  font-size: small;
}
</style>
