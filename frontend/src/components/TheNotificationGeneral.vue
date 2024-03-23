<script setup>
import { ref, watch, computed } from 'vue'

import { useNotificationStore } from '@/stores'

const notificationStore = useNotificationStore()

const isClosing = ref(false)

function close() {
  // TODO_configuration  move animation delay to config file
  isClosing.value = true
  setTimeout(() => {
    notificationStore.deactivate()
    isClosing.value = false
  }, 480)
}

watch(
  computed(() => notificationStore.generalActive),
  (newVal) => {
    if (!newVal) {
      notificationStore.resetGeneralNotification()
    }
    if (newVal) {
      setTimeout(() => {
        if (notificationStore.batchComputeProgressActive) return
        if (notificationStore.deleteProgress) return
        if (notificationStore.calibrationComputing) return
        if (notificationStore.progressActive) return
        if (notificationStore.generalNotification === 'error') {
          setTimeout(close, 10000)
        } else {
          setTimeout(close, 3500)
        }
      }, 1000)
    }
  }
)
</script>

<template>
  <div v-if="notificationStore.generalActive">
    <!-- Submitted Notification -->
    <b-message
      v-if="notificationStore.generalNotification === 'submitted'"
      type="is-notification"
      has-icon
      icon="check-circle"
      :class="{ 'is-closing': isClosing, 'is-submitted': 'is-submitted' }"
    >
      {{ notificationStore.generalNotificationMessage }}
    </b-message>
    <!-- Deleted Notification -->
    <b-message
      v-if="notificationStore.generalNotification === 'deleted'"
      type="is-notification"
      has-icon
      icon="delete-circle"
      :class="{ 'is-closing': isClosing, 'is-error': 'is-error' }"
    >
      {{ notificationStore.generalNotificationMessage }}
    </b-message>
    <!-- Error Notification -->
    <b-message
      v-if="notificationStore.generalNotification === 'error'"
      type="is-notification"
      has-icon
      icon="alert-circle-outline"
      icon-size="is-medium"
      :class="{ 'is-closing': isClosing, 'is-error': 'is-error' }"
    >
      {{ notificationStore.generalNotificationMessage }}
    </b-message>
  </div>
</template>
