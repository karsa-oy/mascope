<script setup>
import Button from 'primevue/button'

import { useApp } from '@/stores'

const app = useApp()
</script>

<template>
  <!-- Opens the bundled user documentation (served by nginx at /docs/) in a new
       tab. Rendered as an anchor so middle/ctrl-click and "open in new tab"
       work. -->
  <Button
    as="a"
    href="/docs/"
    target="_blank"
    rel="noopener"
    icon="pi ph ph-book-open"
    severity="secondary"
    text
    class="docs-button"
    v-tooltip.bottom="'Documentation'"
    aria-label="Open documentation"
    :pt="
      app.ui.help.bottom_end(`
        <h1>Documentation</h1>

        <p>Open the Mascope user guide in a new tab &mdash; concepts, how things
        work, guides and reference.</p>
    `)
    "
  />
</template>

<style scoped>
.docs-button {
  border-radius: 2rem;
}
</style>
