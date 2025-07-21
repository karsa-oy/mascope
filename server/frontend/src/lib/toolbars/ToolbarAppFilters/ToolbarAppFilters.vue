<script setup>
import { ref, computed } from 'vue'

import Toolbar from 'primevue/toolbar'

import { useApp } from '@/stores'
import { BaseKarsaLogo } from '@/lib/base'
import { HelpButton } from '@/lib/help'

import AppFilterChips from './AppFilterChips.vue'
import InstrumentSelector from './InstrumentSelector.vue'

import { SidebarMenu } from './SidebarMenu'

const app = useApp()

const filtering = ref(false)
</script>

<template>
  <Toolbar
    class="filters"
    :pt="
      app.ui.help.bottom(`
        <h1>Main Toolbar</h1>

        <p>Provides controls for global Mascope settings.
        Hover on individual controls for more information.</p>

        <p>Your currently installed version of Mascope is visible
        under the logo. This may be requested from you when
        getting support from Karsa.</p>
      `)
    "
  >
    <template #start>
      <div class="row">
        <SidebarMenu />
      </div>
    </template>
    <template #center>
      <BaseKarsaLogo v-show="!app.data.batch.focused" />
    </template>
    <template #end>
      <div class="row">
        <AppFilterChips v-model:filtering="filtering" v-show="filtering" />
        <InstrumentSelector />
      </div>
    </template>
  </Toolbar>
</template>

<style scoped>
.filters :deep(*) {
  font-size: small;
}

.filters :deep(.p-toolbar) {
  padding: 0.3rem;
}
</style>
