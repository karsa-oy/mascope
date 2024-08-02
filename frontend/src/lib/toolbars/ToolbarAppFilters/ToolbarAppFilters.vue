<script setup>
import Toolbar from 'primevue/toolbar'
import Select from 'primevue/select'
import ContextMenu from 'primevue/contextmenu'
import ToggleSwitch from 'primevue/toggleswitch'
import Popover from 'primevue/popover'
import Button from 'primevue/button'
import Drawer from 'primevue/drawer'
import ScrollPanel from 'primevue/scrollpanel'
import Message from 'primevue/message'
import IconField from 'primevue/iconfield'
import InputIcon from 'primevue/inputicon'
import InputText from 'primevue/inputtext'

import { ref, reactive, computed, watch, watchEffect } from 'vue'

import { BaseKarsaLogo } from '@/lib/base'
import { DialogWorkspaceOp } from '@/lib/dialogs'
import { beautifySnakeCase } from '@/lib/utils'

import { useApp } from '@/stores'

import AcquisitionMode from './AcquisitionMode.vue'

const app = useApp()

const saved = {
  workspace: app.data.workspace.list.find(
    ({ workspace_id }) => workspace_id == localStorage.getItem('mascope-workspace')
  ),
  instrument: app.data.instrument.list.find(
    ({ instrument }) => instrument == localStorage.getItem('mascope-instrument')
  )
}

const dialog = reactive({
  workspace: null
})
const filter = reactive({
  workspace: saved.workspace ?? app.data.workspace.list[0]
})
const settings = ref()
const menu = ref()
const log = reactive({
  query: ''
})

// initial load
app.data.workspace.focus(filter.workspace)

if (saved.instrument) {
  app.data.instrument.focused = saved.instrument
}

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
watch(
  computed(() => app.data.workspace.focused),
  (workspace) => {
    if (workspace && filter.workspace.workspace_id !== workspace.workspace_id) {
      filter.workspace = workspace
    }
  }
)
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

function parseTimestamp(timestamp) {
  const [date, fulltime] = timestamp.toISOString().replace('Z', ' ').slice(0, -1).split('T')
  const [time, ms] = fulltime.split('.')
  return { date, time, ms }
}
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
        <Button
          v-tooltip="'Notifications'"
          icon="pi pi-bell"
          severity="secondary"
          text
          @click="
            (event) => {
              app.ui.notification.drawer = true
            }
          "
        />
        <Drawer
          v-model:visible="app.ui.notification.drawer"
          header="Notifications"
          position="right"
          style="width: 350px"
        >
          <IconField style="width: 100%">
            <InputIcon>
              <i class="pi pi-search" />
            </InputIcon>
            <InputText v-model="log.query" placeholder="Search" style="width: 100%" />
          </IconField>
          <ScrollPanel>
            <Message
              v-for="{
                process_id,
                type,
                status,
                message,
                timestamp
              } in app.ui.notification.log.filter(({ type, status, message }) =>
                `${beautifySnakeCase(type)} ${status} ${message}`.includes(log.query)
              )"
              :key="process_id"
              :severity="
                {
                  warning: 'warn'
                }[status] ?? status
              "
              :closable="false"
            >
              <div class="col" style="gap: 0.5rem">
                <ScrollPanel style="width: 250px">
                  <h4 style="margin: 0.5rem 0">{{ beautifySnakeCase(type) }} {{ status }}</h4>
                  <p style="margin: 0">
                    {{ message }}
                  </p>
                </ScrollPanel>
                <div
                  class="row timestamp"
                  style="width: 250px; opacity: 0.6; justify-content: flex-end; gap: 0"
                  :set="({ date, time, ms } = parseTimestamp(timestamp))"
                >
                  <span>
                    {{ date }}
                  </span>
                  <span style="margin-left: 1rem">{{ time }}</span
                  ><span>.{{ ms }}</span>
                </div>
              </div>
            </Message>
          </ScrollPanel>
        </Drawer>
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
