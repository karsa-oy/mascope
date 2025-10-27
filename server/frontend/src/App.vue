<script setup>
import { onMounted } from 'vue'

import ConfirmDialog from 'primevue/confirmdialog'
import Toast from 'primevue/toast'
import { useToast } from 'primevue/usetoast'
import Panel from 'primevue/panel'
import ProgressSpinner from 'primevue/progressspinner'

import { runtime } from '@/lib/runtime.js'
import { beautifySnakeCase } from '@/lib/utils'
import { BaseKarsaLogo } from '@/lib/base'
import { useApp } from '@/stores'
import { PaneLogin, PaneOwnerSignup } from '@/lib/panes'

const app = useApp()
const toast = useToast()

// toaster
app.ui.notification
  .on('*', (notification) => {
    if (notification === null) return // TODO: Fail-safe, see issue #1008
    const { status, type, message, data, error } = notification
    if (status !== 'pending') {
      const severity =
        {
          warning: 'warn'
        }[status] ?? status

      const duration = status === 'error' ? 10000 : status === 'warning' ? 7000 : 3000

      toast.add({
        severity,
        summary: `${beautifySnakeCase(type)} ${status}`,
        detail: message,
        life: duration
      })

      const download = data?.download ?? error?.detail?.data?.download

      if ((status === 'success' || status === 'warning') && download) {
        const link = document.createElement('a')
        link.download = download
        link.href = `${runtime.api_path}/api/temp/${link.download}`
        link.click()
      }
    }
  })
  .unmount()
</script>

<template>
  <!-- App Routes - Authenticated user -->
  <RouterView v-if="app.auth.user" />
  <!-- Login / Owner Setup Screen - No authenticated user  -->
  <div
    v-else-if="app.auth.user == false && app.auth.requiresOwner !== null"
    class="center"
    style="min-height: 80vh"
  >
    <Panel style="width: 500px">
      <BaseKarsaLogo />
      <div style="margin-top: 2rem" />
      <PaneOwnerSignup v-if="app.auth.requiresOwner" />
      <PaneLogin v-else />
    </Panel>
  </div>

  <!-- Loading - Checking authentication and registration status -->
  <div v-else class="col" style="min-height: 80vh; justify-content: center">
    <BaseKarsaLogo />
    <ProgressSpinner />
    <strong>Identifying user...</strong>
  </div>
  <Toast position="bottom-right" v-if="!app.ui.notification.drawer" />
  <ConfirmDialog />
</template>

<style>
@import './style.css';

#loading {
  width: 100vw;
  height: 100vh;
  display: grid;
  place-items: center;
}
.col {
  gap: 5rem;
}
strong {
  opacity: 0.5;
}
</style>
