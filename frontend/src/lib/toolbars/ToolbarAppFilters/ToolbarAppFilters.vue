<script setup>
import Toolbar from 'primevue/toolbar'
import Select from 'primevue/select'
import ContextMenu from 'primevue/contextmenu'
import ToggleSwitch from 'primevue/toggleswitch'
import Popover from 'primevue/popover'
import Button from 'primevue/button'

import { ref, reactive, computed, watch, watchEffect } from 'vue'

import { BaseKarsaLogo } from '@/lib/base'
import { DialogWorkspaceOp, PopoverUserMenu } from '@/lib/dialogs'
import { runtime } from '@/lib/runtime'

import { useApp } from '@/stores'

import AcquisitionMode from './AcquisitionMode.vue'
import SidebarNotifications from './SidebarNotifications.vue'

const app = useApp()

// Setup initial state
const saved = {
  workspace: null,
  instrument: null
}
const initialWorkspaceLoad = ref(true) // Track initial workspace loading
const initialInstrumentLoad = ref(true) // Track initial instrument loading

// Reactive data
const dialog = reactive({
  workspace: null
})
const filter = reactive({
  workspace: saved.workspace ?? app.data.workspace.list[0]
})
const settings = ref()
const menu = ref()

// Initial loading
/**
 * Watch for when workspace data is initially loaded, then focus on the saved workspace.
 * If the saved workspace is not available, fallback to the first workspace in the list.
 * The watcher only triggers on the first load and is then disabled to avoid conflicts.
 */
watch(
  () => app.data.workspace.list.length,
  (newLength) => {
    if (initialWorkspaceLoad.value && newLength > 0) {
      saved.workspace = app.data.workspace.list.find(
        ({ workspace_id }) => workspace_id === localStorage.getItem('mascope-workspace')
      )
      filter.workspace = saved.workspace ?? app.data.workspace.list[0]
      if (
        filter.workspace &&
        filter.workspace.workspace_id !== app.data.workspace.focused?.workspace_id
      ) {
        app.data.workspace.focus(filter.workspace)
      }
      initialWorkspaceLoad.value = false // Stop watching after the first load
    }
  },
  { immediate: true }
)

/**
 * Watch for when instrument data is loaded, then focus on the saved instrument.
 * If the saved instrument is not available, fallback to the first instrument in the list.
 * The watcher only triggers on the first load and is then disabled to avoid conflicts.
 */
watch(
  () => app.data.instrument.list.length,
  (newLength) => {
    if (initialInstrumentLoad.value && newLength > 0) {
      saved.instrument = app.data.instrument.list.find(
        ({ instrument }) => instrument === localStorage.getItem('mascope-instrument')
      )
      if (saved.instrument) {
        app.data.instrument.focused = saved.instrument
      }
      initialInstrumentLoad.value = false // Disable the watcher after the first load
    }
  },
  { immediate: true }
)

/**
 * Focus the workspace when changed in the toolbar, updating localStorage.
 */
watch(
  computed(() => filter.workspace),
  (workspace) => {
    if (workspace) {
      app.data.workspace.focus(workspace)
      localStorage.setItem('mascope-workspace', workspace.workspace_id)
    } else {
      app.data.workspace.unfocus()
    }
  }
)

/**
 * Sync selected workspace in the toolbar with the focused workspace in app state.
 */
watch(
  computed(() => app.data.workspace.focused),
  (workspace) => {
    if (workspace && filter.workspace.workspace_id !== workspace.workspace_id) {
      filter.workspace = workspace
    }
  }
)

/**
 * Sync focused instrument with the saved one in localStorage.
 */
watch(
  computed(() => app.data.instrument.focused),
  (instrument) => {
    if (instrument) {
      localStorage.setItem('mascope-instrument', instrument.instrument)
    }
  }
)
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
        <div v-tooltip.bottom="filter.workspace?.workspace_description">
          <label for="workspace-selector" class="hidden">Workspace selector</label>
          <Select
            inputId="workspace-selector"
            dataKey="workspace_id"
            v-model="filter.workspace"
            :options="app.data.workspace.list"
            optionLabel="workspace_name"
            style="flex-direction: row-reverse"
            appendTo="self"
          >
            <template #dropdownicon>
              <svg
                xmlns="http://www.w3.org/2000/svg"
                width="22"
                height="22"
                fill="currentColor"
                viewBox="0 0 256 256"
              >
                <path
                  d="M216,72H130.67L102.93,51.2a16.12,16.12,0,0,0-9.6-3.2H40A16,16,0,0,0,24,64V200a16,16,0,0,0,16,16H216.89A15.13,15.13,0,0,0,232,200.89V88A16,16,0,0,0,216,72Zm0,128H40V64H93.33L123.2,86.4A8,8,0,0,0,128,88h88Z"
                ></path>
              </svg>
            </template>
          </Select>
        </div>
        <div id="workspace-menu">
          <Button
            icon="pi pi-ellipsis-h"
            severity="secondary"
            text
            @click="
              (event) => {
                menu.toggle(event)
              }
            "
            class="hiddenlabel"
            label="Workspace menu"
            v-tooltip.right="'Workspace menu'"
          />
          <ContextMenu
            ref="menu"
            appendTo="self"
            :model="[
              {
                label: 'Create workspace',
                icon: 'pi pi-plus',
                command: () => {
                  dialog.workspace = 'create'
                }
              },
              {
                label: 'Edit workspace',
                icon: 'pi pi-pen-to-square',
                command: () => {
                  dialog.workspace = 'edit'
                }
              },
              {
                label: 'Delete workspace',
                icon: 'pi pi-trash',
                command: () => {
                  dialog.workspace = 'delete'
                }
              }
            ]"
          />
        </div>
      </div>
    </template>
    <template #center>
      <BaseKarsaLogo />
    </template>
    <template #end>
      <div class="row">
        <AcquisitionMode />
        <label for="instrument-selector" class="hidden">Instrument selector</label>
        <Select
          inputId="instrument-selector"
          v-model="app.data.instrument.focused"
          :options="app.data.instrument.list"
          dataKey="instrument"
          optionLabel="instrument"
          appendTo="self"
        >
          <template #value="{ value }">
            <span v-if="value?.instrument">
              {{ value.instrument }}
            </span>
            <i v-else> None </i>
          </template>
          <template #dropdownicon>
            <svg
              xmlns="http://www.w3.org/2000/svg"
              width="20"
              height="20"
              fill="currentColor"
              viewBox="0 0 256 256"
            >
              <path
                d="M224,208H203.94A88.05,88.05,0,0,0,144,64.37V32a16,16,0,0,0-16-16H80A16,16,0,0,0,64,32V136a16,16,0,0,0,16,16h48a16,16,0,0,0,16-16V80.46A72,72,0,0,1,181.25,208H32a8,8,0,0,0,0,16H224a8,8,0,0,0,0-16Zm-96-72H80V32h48V136ZM72,184a8,8,0,0,1,0-16h64a8,8,0,0,1,0,16Z"
              ></path>
            </svg>
          </template>
        </Select>
        <SidebarNotifications />
        <PopoverUserMenu />
      </div>
    </template>
  </Toolbar>
  <DialogWorkspaceOp v-model:action="dialog.workspace" />
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
