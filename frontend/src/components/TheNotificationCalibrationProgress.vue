<script setup>
import { ref, watch } from 'vue'

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

watch(notificationStore.calibrationComputing, (value) => {
  if (value) {
    this.activateNotification({
      notification: 'calibrationProgress'
    })
  } else {
    if (notificationStore.active === 'calibrationProgress') {
      close()
    }
  }
})
</script>

<template>
  <div v-if="notificationStore.calibrationProgressActive">
    <b-message
      type="is-notification"
      :title="' Calibration ' + notificationStore.calibrationAction + ' Progress'"
      :closable="true"
      @close="close"
      :class="{ 'is-closing': isClosing }"
    >
      <div>
        <section>
          <p>{{ notificationStore.progressMessage }}</p>
        </section>
        <section class="notification-progress-bar">
          <!-- For m/z Fit -->
          <b-progress
            v-if="notificationStore.calibrationAction === 'm/z Fit'"
            :value="notificationStore.progressPercentage"
            :max="100"
            show-value
            size="is-medium"
            format="percent"
            :type="
              notificationStore.calibrationError
                ? 'is-danger'
                : notificationStore.progressPercentage == 100
                  ? 'is-success'
                  : 'is-primary'
            "
          ></b-progress>
          <!-- For m/z Apply -->
          <b-progress
            v-else-if="notificationStore.calibrationAction === 'm/z Apply'"
            :value="notificationStore.progressPercentage"
            size="is-medium"
            :type="
              notificationStore.progressPercentage == 100
                ? notificationStore.calibrationError
                  ? 'is-danger'
                  : 'is-success'
                : 'is-primary'
            "
          ></b-progress>
          <!-- For m/z Calibrate Batch -->
          <b-progress
            v-else-if="notificationStore.calibrationAction === 'm/z Calibrate Batch'"
            :value="notificationStore.progressPercentage"
            size="is-medium"
            :type="
              notificationStore.progressPercentage == 100
                ? notificationStore.calibrationError
                  ? 'is-danger'
                  : 'is-success'
                : 'is-primary'
            "
          ></b-progress>
        </section>
      </div>
    </b-message>
  </div>
</template>
