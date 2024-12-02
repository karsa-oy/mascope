<script setup>
import Toolbar from 'primevue/toolbar'

import { BaseKarsaLogo } from '@/lib/base'

import AcquisitionMode from './AcquisitionMode.vue'
import SidebarNotifications from './SidebarNotifications.vue'
import SidebarUser from './SidebarUser.vue'
import InstrumentSelector from './InstrumentSelector.vue'
import WorkspaceSelector from './WorkspaceSelector.vue'
</script>

<template>
  <Toolbar class="filters">
    <template #start>
      <div class="row">
        <SidebarUser />
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
