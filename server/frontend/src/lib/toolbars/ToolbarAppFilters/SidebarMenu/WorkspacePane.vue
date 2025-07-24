<script setup>
import { ref, watch, watchEffect, computed } from 'vue'

import Select from 'primevue/select'
import ContextMenu from 'primevue/contextmenu'
import Button from 'primevue/button'
import Listbox from 'primevue/listbox'

import { useApp } from '@/stores'
import { DialogWorkspaceOp } from '@/lib/dialogs'

import { useSidebarMenu } from './state.js'

const app = useApp()
const sidebarMenu = useSidebarMenu()
const open = computed(() => sidebarMenu.open && sidebarMenu.tab === 'workspaces')

const menu = ref()
const dialog = ref()

watch(
  () => app.data.workspace.focused,
  () => {
    if (sidebarMenu.open) {
      sidebarMenu.open = false
    }
  }
)

const layer = 'sidebar_workspaces_tab'
watchEffect(() => {
  if (open.value) {
    app.ui.help.set(layer)
  }
})

const vHelpLayer = app.ui.help.directive(layer)
</script>

<template>
  <div
    v-help-layer.right="
      `
      <b>Workspaces</b>
      
      <p>
        Select and manage workspaces. Workspaces are like folders
        that contain sample batches and their corresponding ion
        mechanism and target configuration.
      </p>`
    "
  >
    <div class="row" style="align-items: center">
      <h2>Workspaces</h2>
      <Button
        icon="pi pi-plus"
        @click="
          (event) => {
            dialog = 'create'
          }
        "
        label="Create"
        style="float: right"
      />
    </div>
    <section>
      <Listbox
        v-model="app.data.workspace.focused"
        :options="app.data.workspace.list"
        optionLabel="worksace_name"
        listStyle="height: calc(100vh - 300px)"
        :pt="
          app.ui.help.bottom_start(`
          <h1>Workspace Selector</h1>

          <p>Workspaces are the like folders that organize samples
          and targets relating to specific projects in one place.
          You can modify, create or delete workspaces by clicking
          the ellipsis icon to the right of the dropdown.</p>
    `)
        "
      >
        <template #option="{ option }">
          <div class="row" style="gap: 1rem">
            <svg
              xmlns="http://www.w3.org/2000/svg"
              width="32"
              height="32"
              fill="currentColor"
              viewBox="0 0 256 256"
              style="opacity: 0.3"
            >
              <path
                d="M216,72H130.67L102.93,51.2a16.12,16.12,0,0,0-9.6-3.2H40A16,16,0,0,0,24,64V200a16,16,0,0,0,16,16H216.89A15.13,15.13,0,0,0,232,200.89V88A16,16,0,0,0,216,72Zm0,128H40V64H93.33L123.2,86.4A8,8,0,0,0,128,88h88Z"
              ></path>
            </svg>
            <div class="col" style="gap: 1rem; align-items: flex-start">
              {{ option.workspace_name }}
              <span style="opacity: 0.5">{{ option.workspace_description }}</span>
            </div>
          </div>
        </template>
      </Listbox>
    </section>
  </div>
  <DialogWorkspaceOp v-model:action="dialog" />
</template>
