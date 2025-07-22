<script setup>
import { ref, watchEffect, computed, provide } from 'vue'

import Button from 'primevue/button'
import Drawer from 'primevue/drawer'
import Tabs from 'primevue/tabs'
import TabList from 'primevue/tablist'
import Tab from 'primevue/tab'
import TabPanels from 'primevue/tabpanels'
import TabPanel from 'primevue/tabpanel'
import ContextMenu from 'primevue/contextmenu'
import OverlayBadge from 'primevue/overlaybadge'

import { DialogWorkspaceOp } from '@/lib/dialogs'

import WorkspacePane from './WorkspacePane.vue'
import UserSettingsPane from './UserSettingsPane.vue'
import NotificationPane from './NotificationPane.vue'

import { api } from '@/api'
import { useApp } from '@/stores'

const app = useApp()

const drawer = ref(false)
const tab = ref('workspaces')
const dialog = ref()
const menu = ref()

const open = defineModel('open')
watchEffect(() => {
  open.value = drawer.value
  tab.value = 'workspaces'
})

provide('sidebar-open', drawer)

/**
 * Computes the badge count to display based on recentErrors or recentWarnings.
 * If there are recent errors, their count is displayed.
 * If there are no errors but warnings, the warning count is displayed.
 * If there are neither, an empty string is returned, hiding the badge.
 *
 *  @returns {String} The badge value as a string.
 */
const badgeValue = computed(() => {
  const errors = app.ui.notification.recentErrors
  const warnings = app.ui.notification.recentWarnings
  return errors > 0 ? String(errors) : warnings > 0 ? String(warnings) : ''
})

/**
 * Determines the severity of the badge.
 * If there are any recent errors, the badge severity is set to 'danger'.
 * Otherwise, if there are only warnings, the badge severity is set to 'warn'.
 *
 * @returns {String} The badge severity ('danger' or 'warn').
 */
const badgeSeverity = computed(() => {
  return app.ui.notification.recentErrors > 0 ? 'danger' : 'warn'
})

/**
 * Controls the visibility of the notification badge.
 * If there are no recent errors or warnings, the badge is hidden.
 *
 * @returns {Boolean} True if the badge should be hidden, otherwise false.
 */
const hiddenBadge = computed(() => {
  return app.ui.notification.recentWarnings === 0 && app.ui.notification.recentErrors === 0
})
</script>

<template>
  <menu class="breadcrum">
    <OverlayBadge :value="badgeValue" :severity="badgeSeverity" size="small">
      <Button
        v-tooltip.bottom="'Home menu'"
        icon="pi ph ph-house"
        severity="secondary"
        text
        @click="
          (event) => {
            drawer = true
          }
        "
      />
    </OverlayBadge>
    <span class="pi ph ph-caret-right" style="opacity: 0.5" />
    <Button
      icon="pi ph ph-folder"
      :label="app.data.workspace.focused?.workspace_name"
      v-tooltip.bottom="
        `${app.data.workspace.focused?.workspace_description}
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
          menu.toggle(event)
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
      />
    </template>
  </menu>
  <Tabs v-model:value="tab">
    <Drawer
      v-model:visible="drawer"
      header="Mascope"
      position="left"
      :style="`width: calc(${app.ui.split.left}vw + 1rem);`"
      :modal="false"
    >
      <template #header>
        <TabList>
          <Tab value="workspaces" v-tooltip.bottom="'Workspaces'">
            <span class="pi ph ph-folder" />
          </Tab>
          <Tab value="notifications" v-tooltip.bottom="'Notifications'"
            ><span class="pi ph ph-bell" />
          </Tab>
          <Tab value="settings" v-tooltip.bottom="'Settings'"
            ><span class="pi ph ph-gear-six" />
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
  <DialogWorkspaceOp v-model:action="dialog" />
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
