<script setup>
import { reactive, computed } from 'vue'

import Button from 'primevue/button'
import Drawer from 'primevue/drawer'
import ScrollPanel from 'primevue/scrollpanel'
import Message from 'primevue/message'
import IconField from 'primevue/iconfield'
import InputIcon from 'primevue/inputicon'
import InputText from 'primevue/inputtext'

import { useApp } from '@/stores'
import { beautifySnakeCase } from '@/lib/utils'

const app = useApp()

const log = reactive({
  query: ''
})

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

function parseTimestamp(timestamp) {
  const [date, fulltime] = timestamp.toISOString().replace('Z', ' ').slice(0, -1).split('T')
  const [time, ms] = fulltime.split('.')
  return { date, time, ms }
}
</script>

<template>
  <Button
    v-tooltip.left="'Notifications'"
    icon="pi pi-bell"
    severity="secondary"
    text
    :badge="badgeValue"
    :badgeSeverity="badgeSeverity"
    class="notification-button"
    :class="{ 'hidden-badge': hiddenBadge }"
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
        v-for="{ process_id, type, status, message, timestamp } in app.ui.notification.log.filter(
          ({ type, status, message }) =>
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
</template>

<style scoped>
.timestamp {
  margin: 0;
}

:deep(.p-scrollpanel-content) {
  padding-bottom: 0.8rem;
}
</style>
