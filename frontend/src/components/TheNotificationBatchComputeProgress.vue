<template>
  <div v-if="notificationIsActive">
    <b-message
      type="is-notification"
      title="Batch Matches Computation Progress"
      :closable="true"
      @close="close"
      :class="{ 'is-closing': isClosing }"
    >
      <div>
        <section>
          <p>{{ progressMessage }}</p>
          <p>{{ currentBatchMessage }}</p>
        </section>
        <section class="notification-progress-bar">
          <b-progress
            :value="progressPercentage"
            :max="100"
            show-value
            size="is-medium"
            format="percent"
            :type="
              computeError
                ? 'is-warning'
                : progressPercentage == 100
                ? 'is-success'
                : 'is-primary'
            "
          ></b-progress>
        </section>
      </div>
    </b-message>
  </div>
</template>

<script>
import { mapMutations, mapState } from "vuex";
import { sync, get, call } from "vuex-pathify";

export default {
  name: "TheNotificationBatchComputeProgress",
  data() {
    return {
      isClosing: false,
    };
  },
  computed: {
    ...sync({
      notificationIsActive: "notification/batchComputeProgressActive",
      progressMessage: "notification/progressMessage",
      currentBatchMessage: "notification/currentBatchMessage",
      progressPercentage: "notification/progressPercentage",
    }),
    ...get({
      batchMatchComputing: "notification/batchMatchComputing",
      notificationActive: "notification/active",
      computeError: "notification/computeError",
    }),
  },
  methods: {
    ...mapMutations({
      activateNotification: "notification/activate",
      deactivateNotification: "notification/deactivate",
    }),
    close() {
      // TODO_configuration  move animation delay to config file
      this.isClosing = true;
      setTimeout(() => {
        this.deactivateNotification();
        this.isClosing = false;
      }, 480);
    },
  },
  watch: {
    batchMatchComputing(value) {
      if (value) {
        this.activateNotification({
          notification: "batchComputeProgress",
        });
      } else {
        if (this.notificationActive === "batchComputeProgress") {
          this.close();
        }
      }
    },
  },
};
</script>
