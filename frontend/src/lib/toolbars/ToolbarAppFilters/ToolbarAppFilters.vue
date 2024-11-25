<script setup>
import Toolbar from 'primevue/toolbar'
import ToggleSwitch from 'primevue/toggleswitch'
import Popover from 'primevue/popover'
import Button from 'primevue/button'

import { ref, reactive, computed, watch, watchEffect } from 'vue'

import { BaseKarsaLogo } from '@/lib/base'
import { PopoverUserMenu } from '@/lib/dialogs'
import { runtime } from '@/lib/runtime'

import { useApp } from '@/stores'

import AcquisitionMode from './AcquisitionMode.vue'
import SidebarNotifications from './SidebarNotifications.vue'
import InstrumentSelector from './InstrumentSelector.vue'
import WorkspaceSelector from './WorkspaceSelector.vue'

const app = useApp()

// Reactive data
const settings = ref()
const menu = ref()

// Initial loading

watchEffect(() => {
  if (app.ui.darkmode.active) {
    document.documentElement.classList.add('darkmode')
    localStorage.setItem('mascope-darkmode', 'true')
  } else {
    document.documentElement.classList.remove('darkmode')
    localStorage.setItem('mascope-darkmode', 'false')
  }
})
</script>

<template>
  <Toolbar class="filters">
    <template #start>
      <div class="row">
        <Button
          v-tooltip="'Settings'"
          icon="pi pi-sliders-h"
          severity="secondary"
          text
          @click="
            (event) => {
              settings.toggle(event)
            }
          "
        />
        <Popover ref="settings">
          <div class="row">
            <span class="pi pi-sun" v-tooltip.bottom="'Light mode'" />
            <ToggleSwitch v-model="app.ui.darkmode.active" />
            <span class="pi pi-moon" v-tooltip.bottom="'Dark mode'" />
          </div>
        </Popover>
        <WorkspaceSelector />
      </div>
    </template>
    <template #center>
      <BaseKarsaLogo />
    </template>
    <template #end>
      <div class="row">
        <AcquisitionMode />
        <InstrumentSelector />
        <SidebarNotifications />
        <PopoverUserMenu />
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

.timestamp {
  margin: 0;
}

:deep(.p-scrollpanel-content) {
  padding-bottom: 0.8rem;
}
</style>
