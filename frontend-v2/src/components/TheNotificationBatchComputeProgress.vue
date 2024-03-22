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

watch(notificationStore.rematchBatchesProgress, (value) => {
  if (value) {
    notificationStore.activate({
      notification: 'batchComputeProgress'
    })
  } else {
    if (notificationStore.active === 'batchComputeProgress') {
      close()
    }
  }
})
watch(notificationStore.rematchBatchProgress, (value) => {
  if (value) {
    notificationStore.activate({
      notification: 'batchComputeProgress'
    })
  } else {
    if (notificationStore.active === 'batchComputeProgress') {
      close()
    }
  }
})
</script>

<template>
  <div v-if="notificationStore.batchComputeProgressActive">
    <b-message
      type="is-notification"
      title="Batch Matches Computation Progress"
      :closable="true"
      @close="close"
      :class="{ 'is-closing': isClosing }"
    >
      <div>
        <section>
          <p>{{ notificationStore.progressMessage }}</p>
          <p>{{ notificationStore.currentBatchMessage }}</p>
        </section>
        <section class="notification-progress-bar">
          <b-progress
            :value="notificationStore.progressPercentage"
            :max="100"
            show-value
            size="is-medium"
            format="percent"
            :type="
              notificationStore.computeError
                ? 'is-warning'
                : notificationStore.progressPercentage == 100
                  ? 'is-success'
                  : 'is-primary'
            "
          ></b-progress>
        </section>
      </div>
    </b-message>
  </div>
</template>
