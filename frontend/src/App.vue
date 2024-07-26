<script setup>
import { computed } from 'vue'

import ProgressSpinner from 'primevue/progressspinner'
import ConfirmDialog from 'primevue/confirmdialog'
import Toast from 'primevue/toast'
import { useToast } from 'primevue/usetoast'

import { beautifySnakeCase } from '@/lib/utils'
import { BaseKarsaLogo } from '@/lib/base'
import { useApp } from '@/stores'

const toast = useToast()

const app = useApp()

const ready = computed(() => app.data.workspace.focused && app.data.instrument.focused)

// toaster
app.notification.on('*', ({ status, type, message }) => {
  if (status !== 'pending') {
    const severity =
      {
        warning: 'warn'
      }[status] ?? status
    toast.add({
      severity,
      summary: `${beautifySnakeCase(type)} ${status}`,
      detail: message,
      life: status === 'error' ? 10000 : 3000
    })
  }
})()

// focus new workspace
app.notification.on('create_workspace', ({ status, data }) => {
  if (status == 'success') {
    const createdWorkspace = app.data.workspace.list.find(
      (workspace) => workspace.workspace_id == data.response.data.workspace_id
    )
    app.data.workspace.focus(createdWorkspace)
  }
})()
</script>

<template>
  <div id="app" v-if="ready">
    <RouterView />
  </div>
  <div id="loading" v-else>
    <div class="col">
      <BaseKarsaLogo />
      <ProgressSpinner />
      <strong>Loading...</strong>
    </div>
  </div>
  <Toast position="bottom-right" v-if="!app.notification.drawer" />
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
