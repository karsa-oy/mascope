<script setup>
import Button from 'primevue/button'
import OverlayBadge from 'primevue/overlaybadge'

import { useApp } from '@/stores'

const app = useApp()
</script>

<template>
  <Button
    icon="pi pi-question-circle"
    :severity="app.ui.help.active ? 'help' : 'secondary'"
    @click="app.ui.help.toggle"
    text
    class="help-button"
    v-tooltip.bottom="'Help mode (alt+h)'"
    :pt="
      app.ui.help.bottom_end(`
        <h1>Help Mode</h1>

        <p>Activate or deactivate help mode, which
        shows cards - such as this one - which explain
        what each feature does.</p>

        <p>You can use the keyboard shortcut <code>alt+h</code>
        to toggle help mode as well.</p>
    `)
    "
  />
</template>

<style scoped>
.help-button {
  border-radius: 2rem;
}
</style>
