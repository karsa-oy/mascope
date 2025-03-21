<script setup>
import { ref, watch } from 'vue'

import Select from 'primevue/select'
import ContextMenu from 'primevue/contextmenu'
import Button from 'primevue/button'

import { useApp } from '@/stores'
import { DialogWorkspaceOp } from '@/lib/dialogs'

const app = useApp()

const menu = ref()
const dialog = ref()
</script>

<template>
  <div v-tooltip.bottom="app.data.workspace?.workspace_description">
    <label for="workspace-selector" class="hidden">Workspace selector</label>
    <Select
      inputId="workspace-selector"
      dataKey="workspace_id"
      v-model="app.data.workspace.focused"
      :options="app.data.workspace.list"
      optionLabel="workspace_name"
      style="flex-direction: row-reverse"
      appendTo="self"
      v-tooltip.right="'Workspace'"
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
            dialog = 'create'
          }
        },
        {
          label: 'Edit workspace',
          icon: 'pi pi-pen-to-square',
          command: () => {
            dialog = 'edit'
          }
        },
        {
          label: 'Delete workspace',
          icon: 'pi pi-trash',
          command: () => {
            dialog = 'delete'
          }
        }
      ]"
    />
  </div>
  <DialogWorkspaceOp v-model:action="dialog" />
</template>
