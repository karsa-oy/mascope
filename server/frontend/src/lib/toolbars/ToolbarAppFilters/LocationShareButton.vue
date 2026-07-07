<script setup>
import { computed } from 'vue'

import Button from 'primevue/button'

import { useApp } from '@/stores'
import { useLocation, isEmptyLocation } from '@/lib/location'

const app = useApp()
const location = useLocation()

// Only offer a link once there is something worth sharing (a selection exists).
const shareable = computed(() => !isEmptyLocation(location.read()))
</script>

<template>
  <Button
    v-show="shareable"
    icon="ph ph-link-simple"
    severity="secondary"
    text
    rounded
    aria-label="Copy link to this view"
    :pt="
      app.ui.help.bottom(`
        <h1>Share this view</h1>
        <p>Copy a link that reopens Mascope at the current selection. Anyone you
        share it with lands here, provided they can access the same data.</p>
      `)
    "
    @click="location.copyShareLink()"
  />
</template>
