<script setup>
import { computed, watch } from 'vue'

import ProgressSpinner from 'primevue/progressspinner'
import ConfirmDialog from 'primevue/confirmdialog'
import Toast from 'primevue/toast'
import { useToast } from 'primevue/usetoast'

import { beautifySnakeCase } from '@/lib/utils'
import { BaseKarsaLogo } from '@/lib/base'
import { useApp } from '@/stores'

const toast = useToast()

const app = useApp()

const ready = computed(() => app.data.workspace.list.length > 0)

// toaster
app.ui.notification
  .on('*', ({ status, type, message }) => {
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
    }
  })
  .unmount()

/**
 * Watch for when workspace data is loaded, then focus on the saved workspace.
 * If the saved workspace is not available, fallback to the first workspace in the list.
 */
watch(
  () => app.data.workspace.list.length,
  (newLength) => {
    if (newLength > 0) {
      const savedWorkspaceId = localStorage.getItem('mascope-workspace')
      const workspaceIdToFocus = savedWorkspaceId || app.data.workspace.list[0]?.workspace_id // Fallback to the first workspace ID
      if (workspaceIdToFocus) {
        app.data.workspace.focus({ workspace_id: workspaceIdToFocus })
      }
    }
  }
)

/**
 * Watch for when instrument data is loaded, then focus on the saved instrument.
 * If the saved instrument is not available, fallback to the first instrument in the list.
 */
watch(
  () => app.data.instrument.list.length,
  (newLength) => {
    if (newLength > 0) {
      const savedInstrumentName = localStorage.getItem('mascope-instrument')
      const instrumentToFocus = savedInstrumentName || app.data.instrument.list[0]?.instrument // Fallback to the first instrument
      if (instrumentToFocus) {
        app.data.instrument.focus({ instrument: instrumentToFocus })
      }
    }
  }
)

// focus new workspace
app.ui.notification
  .on('create_workspace', ({ status, data }) => {
    if (status == 'success') {
      const createdWorkspace = app.data.workspace.list.find(
        (workspace) => workspace.workspace_id == data.response.data.workspace_id
      )
      app.data.workspace.focus(createdWorkspace)
    }
  })
  .unmount()
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
