<script setup>
import { ref, watchEffect } from 'vue'

import Button from 'primevue/button'
import Drawer from 'primevue/drawer'
import Tabs from 'primevue/tabs'
import TabList from 'primevue/tablist'
import Tab from 'primevue/tab'
import TabPanels from 'primevue/tabpanels'
import TabPanel from 'primevue/tabpanel'
import ContextMenu from 'primevue/contextmenu'

import { DialogWorkspaceOp } from '@/lib/dialogs'
import { BatchContextMenu, useBatchContextMenu } from '@/lib/panes'

import { useSidebarMenu } from './state.js'
import WorkspacePane from './WorkspacePane.vue'
import UserSettingsPane from './UserSettingsPane.vue'
import NotificationPane from './NotificationPane.vue'
import NotificationOverlay from './NotificationOverlay.vue'

import { useApp } from '@/stores'

const app = useApp()
const sidebarMenu = useSidebarMenu()

const dialog = ref()
const workspaceContextMenu = ref()
const batchContextMenu = useBatchContextMenu()

watchEffect(() => {
  if (!sidebarMenu.open) {
    sidebarMenu.tab = 'workspaces'
  }
})

watchEffect(() => {
  if (sidebarMenu.open && sidebarMenu.tab === 'notifications') {
    app.ui.notification.clearRecentBadge()
  }
})
watchEffect(() => {
  if (!sidebarMenu.open) {
    app.ui.help.set(null)
  }
})
</script>

<template>
  <menu class="breadcrum">
    <NotificationOverlay>
      <Button
        v-tooltip.bottom="'Home menu'"
        icon="pi ph ph-house"
        severity="secondary"
        text
        @click="
          (event) => {
            sidebarMenu.open = true
          }
        "
      />
    </NotificationOverlay>
    <span class="pi ph ph-caret-right" style="opacity: 0.5" />
    <Button
      icon="pi ph ph-folder"
      :label="app.data.workspace.focused?.workspace_name"
      v-tooltip.bottom="
        `${app.data.workspace.focused?.workspace_description ?? 'No description'}
                         (right click for options)`
      "
      severity="secondary"
      text
      @click="
        () => {
          app.data.batch.unfocus()
        }
      "
      @contextmenu="
        (event) => {
          event.preventDefault()
          workspaceContextMenu.toggle(event)
        }
      "
    />
    <template v-if="app.data.batch.focused">
      <span class="pi ph ph-caret-right" style="opacity: 0.5" />
      <Button
        icon="pi pi-tags"
        :label="app.data.batch.focused.sample_batch_name"
        severity="secondary"
        text
        @click="
          () => {
            app.data.sample.unfocus()
          }
        "
        @contextmenu="
          (event) => {
            event.preventDefault()
            batchContextMenu.onClick(event)
          }
        "
      />
    </template>
  </menu>
  <Tabs v-model:value="sidebarMenu.tab">
    <Drawer
      v-model:visible="sidebarMenu.open"
      header="Mascope"
      position="left"
      :style="`width: calc(${app.ui.split.left}vw + 1rem);`"
      :modal="false"
      :dismissable="false"
    >
      <template #header>
        <TabList>
          <Tab value="workspaces" v-tooltip.bottom="'Workspaces'">
            <span class="pi ph ph-folder" />
          </Tab>
          <Tab value="notifications" v-tooltip.bottom="'Notifications'">
            <NotificationOverlay>
              <span class="pi ph ph-bell" />
            </NotificationOverlay>
          </Tab>
          <Tab value="settings" v-tooltip.bottom="'Settings'">
            <span class="pi ph ph-gear-six" />
          </Tab>
        </TabList>
      </template>
      <TabPanels>
        <TabPanel value="workspaces">
          <WorkspacePane />
        </TabPanel>
        <TabPanel value="notifications">
          <NotificationPane />
        </TabPanel>
        <TabPanel value="settings">
          <UserSettingsPane />
        </TabPanel>
      </TabPanels>
      <template #footer>
        <div class="row">
          <span class="user-info">Logged in as {{ app.auth.user.username }}</span>
          <Button
            icon="pi pi-sign-out"
            label="Logout"
            @click="app.auth.logout"
            style="margin-top: 1rem"
          />
        </div>
      </template>
    </Drawer>
  </Tabs>
  <ContextMenu
    ref="workspaceContextMenu"
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
  <DialogWorkspaceOp v-model:action="dialog" />
  <BatchContextMenu />
</template>

<style scoped>
section:not(:first-child) {
  margin-top: 1rem;
  border-top: 1px solid var(--p-drawer-border-color);
}

.p-tab span {
  width: 40px;
  font-size: 1.2rem;
}

:deep(.p-badge) {
  font-size: 8px !important;
  line-height: 8px !important;
  height: 10px !important;
  min-width: 10px !important;
}

.row {
  align-items: baseline;

  .user-info {
    font-size: 1rem;
    width: fit-content;
    opacity: 0.7;
  }
}

.breadcrum {
  display: flex;
  flex-flow: row;
  gap: 0.3rem;
  align-items: center;
  padding: 0;

  .p-button {
    padding: 0.1rem 0.5rem;
    border-radius: 1rem;

    &:first-child {
      padding: 0.1rem;
    }
  }
}
</style>
