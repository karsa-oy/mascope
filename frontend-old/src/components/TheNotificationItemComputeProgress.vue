<template>
  <div v-if="notificationIsActive">
    <b-message
      type="is-notification"
      title="Sample Matches Computation Progress"
      :closable="true"
      @close="close"
      :class="{ 'is-closing': isClosing }"
    >
      <div>
        <section>
          <p>{{ progressMessage }}</p>
        </section>
        <section class="notification-progress-bar">
          <b-progress
            :value="progressPercentage"
            :max="100"
            show-value
            size="is-medium"
            format="percent"
            :type="
              computeError ? 'is-danger' : progressPercentage == 100 ? 'is-success' : 'is-primary'
            "
          ></b-progress>
        </section>
      </div>
    </b-message>
  </div>
</template>

<script>
import { mapMutations, mapState } from 'vuex'
import { sync, get, call } from 'vuex-pathify'

export default {
  name: 'TheNotificationItemComputeProgress',
  data() {
    return {
      isClosing: false,
    }
  },
  computed: {
    ...sync({
      notificationIsActive: 'notification/itemComputeProgressActive',
      progressMessage: 'notification/progressMessage',
      progressPercentage: 'notification/progressPercentage',
    }),
    ...get({
      itemMatchComputing: 'notification/itemMatchComputing',
      notificationActive: 'notification/active',
      computeError: 'notification/computeError',
    }),
  },
  methods: {
    ...mapMutations({
      activateNotification: 'notification/activate',
      deactivateNotification: 'notification/deactivate',
    }),
    close() {
      // TODO_configuration  move animation delay to config file
      this.isClosing = true
      setTimeout(() => {
        this.deactivateNotification()
        this.isClosing = false
      }, 480)
    },
  },
  watch: {
    itemMatchComputing(value) {
      if (value) {
        this.activateNotification({
          notification: 'itemComputeProgress',
        })
      } else {
        if (this.notificationActive === 'itemComputeProgress') {
          this.close()
        }
      }
    },
  },
}
</script>
