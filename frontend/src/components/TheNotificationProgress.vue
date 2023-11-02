<template>
  <div v-if="notificationIsActive">
    <b-message
      type="is-notification"
      :title="progressTitle"
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
            v-if="progressPercentage === 0"
            size="is-medium"
            :type="progressType"
          ></b-progress>
          <b-progress
            v-else
            :value="progressPercentage"
            size="is-medium"
            :type="progressType"
          ></b-progress>
        </section>
      </div>
    </b-message>
  </div>
</template>

<script>
import { mapMutations, mapState } from "vuex";
import { sync, get } from "vuex-pathify";

export default {
  name: "TheNotificationProgress",
  data() {
    return {
      isClosing: false,
    };
  },
  computed: {
    ...sync({
      notificationIsActive: "notification/progressActive",
      progressAction: "notification/progressAction",
      progressActionType: "notification/progressActionType",
      progressMessage: "notification/progressMessage",
      progressPercentage: "notification/progressPercentage",
      progressData: "notification/progressData",
      progressError: "notification/progressError",
    }),
    progressTitle() {
      switch (this.progressAction) {
        // case "calibration":
        //   return `Calibration ${this.calibrationAction} Progress`;
        case "copy":
          return `Copy ${this.progressActionType} Progress`;
        case "delete":
          return `Deleting ${this.progressActionType} Progress`;
      }
    },
    progressType() {
      switch (this.progressAction) {
        case "delete":
          return this.progressError
            ? "is-danger"
            : this.progressPercentage === 100
            ? "is-success"
            : "is-primary";
        case "copy":
          return this.progressError
            ? "is-danger"
            : this.progressPercentage === 100
            ? "is-success"
            : "is-primary";
      }
    },
    // Dynamically compute the name of the progress state based on the action
    progressStateName() {
      return this.progressAction ? this.progressAction + "Progress" : null;
    },
    // Fetch the progress state value dynamically from the store
    progressStateValue() {
      return this.progressStateName
        ? this.$store.state.notification[this.progressStateName]
        : false;
    },
  },
  methods: {
    ...mapMutations({
      activateNotification: "notification/activate",
      deactivateNotification: "notification/deactivate",
    }),
    close() {
      this.isClosing = true;
      setTimeout(() => {
        this.deactivateNotification();
        this.isClosing = false;
      }, 480);
    },
  },
  watch: {
    progressStateValue(newValue, oldValue) {
      if (newValue && !oldValue) {
        // If the value has changed from false to true, activate the notification
        this.activateNotification({
          notification: "progress",
        });
      } else if (!newValue && oldValue) {
        // If the value has changed from true to false, close the notification
        this.close();
      }
    },
  },
};
</script>
