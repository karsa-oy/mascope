<script setup>
import { reactive, computed, inject } from 'vue'

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

const open = inject('sidebar-open')

function parseTimestamp(timestamp) {
  const [date, fulltime] = timestamp.toISOString().replace('Z', ' ').slice(0, -1).split('T')
  const [time, ms] = fulltime.split('.')
  return { date, time, ms }
}
</script>

<template>
  <h2>Notifications</h2>
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
          :set="{ date, time, ms } = parseTimestamp(timestamp)"
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
</template>

<style scoped>
.timestamp {
  margin: 0;
}

:deep(.p-scrollpanel-content) {
  padding-bottom: 0.8rem;
}

:deep(.p-message) {
  margin: 1rem 0;
}
</style>
