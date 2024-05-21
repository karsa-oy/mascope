<script setup>
import Toolbar from 'primevue/toolbar'
import Select from 'primevue/select'
import ContextMenu from 'primevue/contextmenu'
import ToggleSwitch from 'primevue/toggleswitch'
import Popover from 'primevue/popover'
import Button from 'primevue/button'

import { ref, reactive, computed, watch, watchEffect } from 'vue'

import { BaseKarsaLogo } from '@/lib/base'
import { ModeMeasurement } from '@/lib/modes'
import { DialogWorkspaceOp } from '@/lib/dialogs'

import { useAppStore, useWorkspaceStore, useInstrumentStore } from '@/stores'

const appStore = useAppStore()
const workspaceStore = useWorkspaceStore()
const instrumentStore = useInstrumentStore()

const saved = {
  workspace: appStore.workspaces.find(
    ({ workspace_id }) => workspace_id == localStorage.getItem('mascope-workspace')
  ),
  instrument: appStore.instruments.find(
    ({ instrument }) => instrument == localStorage.getItem('mascope-instrument')
  )
}

const dialog = reactive({
  workspace: null
})
const filter = reactive({
  workspace: saved.workspace ?? appStore.workspaces[0]
})
const settings = ref()
const menu = ref()

// initial load
workspaceStore.load(filter.workspace.workspace_id)

if (saved.instrument) {
  instrumentStore.active = saved.instrument
}

watch(
  computed(() => filter.workspace),
  (workspace) => {
    if (workspace) {
      workspaceStore.load(workspace.workspace_id)
      localStorage.setItem('mascope-workspace', workspace.workspace_id)
    } else {
      workspaceStore.unload()
    }
  }
)
watch(
  computed(() => workspaceStore.active),
  (workspace) => {
    if (workspace && filter.workspace.workspace_id !== workspace.workspace_id) {
      filter.workspace = workspace
    }
  }
)
watch(
  computed(() => instrumentStore.active),
  (instrument) => {
    if (instrument) {
      localStorage.setItem('mascope-instrument', instrument.instrument)
    }
  }
)
watchEffect(() => {
  if (appStore.mode.dark) {
    document.body.classList.add('darkmode')
    localStorage.setItem('mascope-darkmode', 'true')
  } else {
    document.body.classList.remove('darkmode')
    localStorage.setItem('mascope-darkmode', 'false')
  }
})
</script>

<template>
  <Toolbar class="k-filters">
    <template #start>
      <div class="row">
        <Button
          v-tooltip.bottom="'Settings'"
          icon="pi pi-sliders-h"
          severity="secondary"
          @click="
            (event) => {
              settings.toggle(event)
            }
          "
        />
        <Popover ref="settings">
          <div class="row">
            <span class="pi pi-sun" v-tooltip.bottom="'Light mode'" />
            <ToggleSwitch v-model="appStore.mode.dark" />
            <span class="pi pi-moon" v-tooltip.bottom="'Dark mode'" />
          </div>
        </Popover>
        <div v-tooltip.bottom="filter.workspace?.workspace_description">
          <label for="workspace-selector" class="hidden">Workspace selector</label>
          <Select
            inputId="workspace-selector"
            dataKey="workspace_id"
            v-model="filter.workspace"
            :options="appStore.workspaces"
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
                menu.show(event)
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
        <ModeMeasurement />
        <label for="instrument-selector" class="hidden">Instrument selector</label>
        <Select
          inputId="instrument-selector"
          v-model="instrumentStore.active"
          :options="appStore.instruments"
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
      </div>
    </template>
  </Toolbar>
  <DialogWorkspaceOp v-model:action="dialog.workspace" />
</template>

<style scoped>
.k-filters :deep(*) {
  font-size: small;
}

.k-filters :deep(.p-toolbar) {
  padding: 0.3rem;
}
</style>
