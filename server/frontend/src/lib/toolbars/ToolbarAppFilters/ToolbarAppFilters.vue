<script setup>
import { ref } from 'vue'

import Toolbar from 'primevue/toolbar'

import { useApp } from '@/stores'
import { BaseKarsaLogo } from '@/lib/base'
import { HelpButton } from '@/lib/help'

import AppFilterChips from './AppFilterChips.vue'
import AcquisitionMode from './AcquisitionMode.vue'
import SidebarNotifications from './SidebarNotifications.vue'
import SidebarUser from './SidebarUser.vue'
import InstrumentSelector from './InstrumentSelector.vue'
import WorkspaceSelector from './WorkspaceSelector.vue'

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
        <SidebarUser />
        <WorkspaceSelector />
      </div>
    </template>
    <template #center>
      <AppFilterChips v-model:filtering="filtering" v-show="filtering" />
      <BaseKarsaLogo v-show="!filtering" />
    </template>
    <template #end>
      <div class="row">
        <AcquisitionMode />
        <InstrumentSelector />
        <HelpButton />
        <SidebarNotifications />
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
