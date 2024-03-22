<script setup>
import { ref, watch, computed } from 'vue'

import { useNotificationStore } from '@/stores'

const notificationStore = useNotificationStore()

const isClosing = ref(false)

const valueProgressActions = ['matchCompute', 'calibration', 'export']

function close() {
  // TODO_configuration  move animation delay to config file
  isClosing.value = true
  setTimeout(() => {
    notificationStore.deactivate()
    isClosing.value = false
  }, 480)
}

const progressTitle = computed(() => {
  const actionTypeCapitalized =
    notificationStore.progressActionType.charAt(0).toUpperCase() +
    notificationStore.progressActionType.slice(1)

  switch (notificationStore.progressAction) {
    case 'copy':
      return `Copy ${actionTypeCapitalized} Progress`
    case 'delete':
      return `Deleting ${actionTypeCapitalized} Progress`
    case 'export':
      return `Export ${actionTypeCapitalized} Progress`
    case 'import':
      return `Import ${actionTypeCapitalized} Progress`
    default:
      return `${
        notificationStore.progressAction.charAt(0).toUpperCase() +
        notificationStore.progressAction.slice(1)
      } Progress`
  }
})
const progressType = computed(() => {
  return notificationStore.progressError
    ? 'is-danger'
    : notificationStore.progressPercentage === 100
      ? 'is-success'
      : 'is-primary'
})
// Dynamically compute the name of the progress state based on the action
const progressStateName = computed(() =>
  notificationStore.progressAction ? notificationStore.progressAction + 'Progress' : null
)
// Fetch the progress state value dynamically from the store
const progressStateValue = computed(() =>
  progressStateName.value ? notificationStore[progressStateName.value] : false
)

watch(progressStateValue, (newValue, oldValue) => {
  if (newValue && !oldValue) {
    // If the value has changed from false to true, activate the notification
    notificationStore.activate({
      notification: 'progress'
    })
  } else if (!newValue && oldValue) {
    // If the value has changed from true to false, close the notification
    close()
  }
})
</script>

<template>
  <div v-if="notificationStore.progressActive">
    <b-message
      type="is-notification"
      :title="progressTitle"
      :closable="true"
      @close="close"
      :class="{ 'is-closing': isClosing }"
    >
      <div>
        <section>
          <p>{{ notificationStore.progressMessage }}</p>
          <p v-if="notificationStore.progressDataMessage">
            {{ notificationStore.progressDataMessage }}
          </p>
        </section>
        <section class="notification-progress-bar">
          <b-progress
            v-if="notificationStore.progressPercentage === 0"
            size="is-medium"
            :type="progressType"
          ></b-progress>
          <b-progress
            v-else-if="valueProgressActions.includes(notificationStore.progressAction)"
            :value="notificationStore.progressPercentage"
            :max="100"
            show-value
            size="is-medium"
            format="percent"
            :type="progressType"
          ></b-progress>
          <b-progress
            v-else
            :value="notificationStore.progressPercentage"
            size="is-medium"
            :type="progressType"
          ></b-progress>
        </section>
      </div>
    </b-message>
  </div>
</template>
