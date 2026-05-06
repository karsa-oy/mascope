<script setup>
import { ref, watch, watchEffect, computed, nextTick } from 'vue'

import Button from 'primevue/button'
import Listbox from 'primevue/listbox'
import ContextMenu from 'primevue/contextmenu'

import { useApp } from '@/stores'
import { DialogWorkspaceOp, DialogWorkspaceMembership } from '@/lib/dialogs'

import { useSidebarMenu } from './state.js'

const app = useApp()
const sidebarMenu = useSidebarMenu()
const open = computed(() => sidebarMenu.open && sidebarMenu.tab === 'workspaces')

const dialog = ref()
const membersDialog = ref(false)
const workspaceContextMenu = ref()
const selectedWorkspace = ref(null)

watch(
  () => app.data.workspace.focused,
  async (value) => {
    if (value && sidebarMenu.open) {
      await nextTick()
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
        Select and manage workspaces. Workspaces group workspaces together
        and serve as the access control boundary. Click on a workspace to select it.
      </p>
      <p>Click on the Create button to create a new workspace.</p>
      `
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
        :modelValue="app.data.workspace.focused"
        @update:modelValue="
          (value) => {
            if (value) {
              app.data.workspace.focused = value
            } else if (!value && sidebarMenu.open) {
              sidebarMenu.open = false
            }
          }
        "
        @contextmenu.prevent
        filter
        :filterPlaceholder="'Search workspaces'"
        :options="app.data.workspace.list"
        optionLabel="workspace_name"
        listStyle="height: calc(100vh - 300px)"
      >
        <template #option="{ option }">
          <div
            class="row"
            style="gap: 1rem; width: 100%; justify-content: flex-start"
            :style="option.is_member === false ? { opacity: 0.45 } : {}"
            @contextmenu="
              (event) => {
                event.preventDefault()
                selectedWorkspace = option
                workspaceContextMenu.toggle(event)
              }
            "
          >
            <span class="pi ph ph-briefcase" style="font-size: 1.5rem; opacity: 0.3" />
            <div class="col" style="gap: 1rem; align-items: flex-start">
              {{ option.workspace_name }}
              <span style="opacity: 0.5">{{ option.workspace_description }}</span>
            </div>
          </div>
        </template>
      </Listbox>
    </section>
  </div>
  <ContextMenu
    ref="workspaceContextMenu"
    appendTo="self"
    :model="[
      {
        label: 'Manage members',
        icon: 'pi pi-users',
        command: () => {
          membersDialog = true
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
  <DialogWorkspaceOp v-model:action="dialog" :workspace="selectedWorkspace" />
  <DialogWorkspaceMembership v-model:visible="membersDialog" :workspace="selectedWorkspace" />
</template>
